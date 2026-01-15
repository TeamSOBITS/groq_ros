import os
import cv2
import yaml
import base64

from groq import Groq
from rcl_interfaces.msg import ParameterDescriptor, ParameterType

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

import ament_index_python
from cv_bridge import CvBridge

from sensor_msgs.msg import Image
from sobits_interfaces.action import ChatLlmRecognition


class GroqActionServer(Node):
    def __init__(self):
        super().__init__('groq_action_server')
        
        self.callback_group = ReentrantCallbackGroup()
                
        self.declare_parameter('rooms_file', '')
        self.declare_parameter('api_key', '')
        self.declare_parameter('groq.temperature', 1.0)
        self.declare_parameter('groq.json_mode', False)
        self.declare_parameter('groq.max_completion_tokens', 4096) 
        self.declare_parameter('groq.top_p', 1.0)
        self.declare_parameter('groq.seed', -1)
        self.declare_parameter('groq.presence_penalty', 0.0)
        self.declare_parameter('groq.frequency_penalty', 0.0)

        self.room_file = self.get_parameter('rooms_file').value
        self.api_key = self.get_parameter('api_key').value
        self.pkg_path = ament_index_python.get_package_share_directory('groq_ros')
        self.config_path = os.path.join(self.pkg_path, 'config/')

        if not os.path.exists(self.config_path):
            os.makedirs(self.config_path, exist_ok=True)
   
        self.groq_params = {
            'temperature': self.get_parameter('groq.temperature').value,
            'json_mode': self.get_parameter('groq.json_mode').value,
            'max_completion_tokens': self.get_parameter('groq.max_completion_tokens').value,
            'top_p': self.get_parameter('groq.top_p').value,
            'seed': self.get_parameter('groq.seed').value,
            'presence_penalty': self.get_parameter('groq.presence_penalty').value,
            'frequency_penalty': self.get_parameter('groq.frequency_penalty').value,
        }

        self.get_logger().info(f'API Key: {"[HIDDEN]" if self.api_key else "[NOT SET]"}')        
        if not self.api_key:
            self.get_logger().error('API Key is not set. Node will shutdown.')
            raise RuntimeError('API Key is missing')

        try:
            with open(self.room_file, "r") as file:
                self.rooms = yaml.safe_load(file)
        except Exception as e:
            self.get_logger().warn(f'Failed to load room file: {e}')
            self.rooms = {}

        self.groq_client = Groq(api_key=self.api_key)
        self.chat_messages = {}
        self.build_prompt() 
        self.bridge = CvBridge() 

        self.action_server_ = ActionServer(
            self, 
            ChatLlmRecognition, 
            "groq_action",
            execute_callback=self.groq_callback, 
            callback_group=self.callback_group,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback
        )
        YELLOW = '\033[93m'
        ENDC = '\033[0m'
        self.get_logger().info(f"{YELLOW}Groq Server is READY and waiting for requests.{ENDC}")

    def goal_callback(self, goal_request):
        self.get_logger().info('Received goal request')
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info('Received cancel request and accepted.')
        return CancelResponse.ACCEPT

    def groq_callback(self, goal_handle):
        self.get_logger().info(f'Executing goal: {goal_handle.request.request}')

        response = ChatLlmRecognition.Result()
        room = goal_handle.request.room_name if goal_handle.request.room_name else 'default'
        
        if room not in self.chat_messages:
            self.chat_messages[room] = []

        current_content = [{"type": "text", "text": goal_handle.request.request}]

        for path in goal_handle.request.sound_file_path:
            if os.path.exists(path):
                mime_type = "image/jpeg" if path.lower().endswith(('.jpg', '.jpeg')) else "image/png"
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                current_content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}})

        for img_msg in goal_handle.request.image:
            img_cv = self.bridge.imgmsg_to_cv2(img_msg, desired_encoding='bgr8')
            success, buffer = cv2.imencode('.jpg', img_cv)
            if success:
                b64 = base64.b64encode(buffer).decode('utf-8')
                current_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        self.chat_messages[room].append({'role': 'user', 'content': current_content})

        feedback = ChatLlmRecognition.Feedback()
        feedback.wip_result = ""
        starting_time = self.get_clock().now()

        try:
            request_params = {
                "model": goal_handle.request.model_name,
                "messages": self.chat_messages[room],
                "temperature": self.groq_params['temperature'],
                "max_completion_tokens": self.groq_params['max_completion_tokens'],
                "top_p": self.groq_params['top_p'],
                "presence_penalty": self.groq_params['presence_penalty'],
                "frequency_penalty": self.groq_params['frequency_penalty'],
                "stream": True
            }

            if self.groq_params['json_mode']:
                request_params["response_format"] = {"type": "json_object"}
            if self.groq_params['seed'] >= 0:
                request_params["seed"] = self.groq_params['seed']

            raw_res = self.groq_client.chat.completions.with_raw_response.create(**request_params)
            remaining_day = raw_res.headers.get('x-ratelimit-remaining-day') or raw_res.headers.get('x-ratelimit-remaining-requests')
            self.get_logger().info(f'[Rate Limit] {remaining_day} requests remaining for today.')
            
            completion = raw_res.parse()

            for chunk in completion:
                if goal_handle.is_cancel_requested:
                    self.get_logger().info('Goal cancel requested. Stopping stream.')
                    if self.chat_messages[room]:
                        self.chat_messages[room].pop()
                    goal_handle.canceled()
                    return response
                
                content = chunk.choices[0].delta.content
                if content:
                    feedback.wip_result += content
                    goal_handle.publish_feedback(feedback)

            ending_time = self.get_clock().now()
            response.elapsed_time = (ending_time - starting_time).nanoseconds / 1e9
            response.result = feedback.wip_result

            if goal_handle.request.is_stack:
                self.chat_messages[room].append({'role': 'assistant', 'content': response.result})
            else:
                if self.chat_messages[room]:
                    self.chat_messages[room].pop()

            goal_handle.succeed()
            self.get_logger().info('Goal succeeded.')
            return response

        except Exception as e:
            if room in self.chat_messages and self.chat_messages[room]:
                self.chat_messages[room].pop()
            self.get_logger().error(f'Groq API Error: {str(e)}')
            goal_handle.abort()
            return response

    def build_prompt(self):
        self.chat_messages = {}
        if not self.rooms: return 
        for room_name, history in self.rooms.items():
            self.chat_messages[str(room_name)] = []
            for talk in history:
                content_list = []
                if "system" in talk:
                    role = "system"
                    text = talk["system"]
                elif "user" in talk:
                    role = "user"
                    text = talk["user"]
                elif "model" in talk:
                    role = "assistant"
                    text = talk["model"]
                else:
                    continue 
                content_list.append({"type": "text", "text": text})

                if "files" in talk and role != "system":
                    for f in talk["files"]:
                        path = f if f.startswith("/") else os.path.join(self.config_path, f)
                        if os.path.exists(path):
                            with open(path, "rb") as img_file:
                                b64 = base64.b64encode(img_file.read()).decode('utf-8')
                                content_list.append({
                                    "type": "image_url", 
                                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                                })
                self.chat_messages[str(room_name)].append({"role": role, "content": content_list})

def main(args=None):
    rclpy.init(args=args)
    executor = MultiThreadedExecutor()
    node = None
    try:
        node = GroqActionServer()
        executor.add_node(node)
        executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    except RuntimeError as e:
        print(f"Runtime Error: {e}")
    finally:
        if rclpy.ok():
            if node:
                node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()