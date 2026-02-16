import os
import cv2
import yaml
import json
import base64

from groq import Groq
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

import ament_index_python
from cv_bridge import CvBridge

from sensor_msgs.msg import Image
from rcl_interfaces.msg import SetParametersResult
from sobits_interfaces.action import ChatLlmRecognition

class GroqActionServer(Node):
    def __init__(self):
        super().__init__('groq_action_server')
        
        self.callback_group = ReentrantCallbackGroup()
        self.declare_parameter('rooms_file', '')
        self.declare_parameter('function_list_file', '')      
        self.declare_parameter('api_key', '')
        self.declare_parameter('groq.temperature', 1.0)
        self.declare_parameter('groq.json_mode', False)
        self.declare_parameter('groq.max_completion_tokens', 4096) 
        self.declare_parameter('groq.top_p', 1.0)
        self.declare_parameter('groq.seed', -1)
        self.declare_parameter('groq.presence_penalty', 0.0)
        self.declare_parameter('groq.frequency_penalty', 0.0)
        self.declare_parameter('groq.tool_choice', 'required') 

        self.room_file = self.get_parameter('rooms_file').value
        self.function_list_file = self.get_parameter('function_list_file').value
        self.api_key = self.get_parameter('api_key').value
        self.pkg_path = ament_index_python.get_package_share_directory('groq_ros')
        self.config_path = os.path.join(self.pkg_path, 'config/')

        self.groq_params = {
            'temperature': self.get_parameter('groq.temperature').value,
            'json_mode': self.get_parameter('groq.json_mode').value,
            'max_completion_tokens': self.get_parameter('groq.max_completion_tokens').value,
            'top_p': self.get_parameter('groq.top_p').value,
            'seed': self.get_parameter('groq.seed').value,
            'presence_penalty': self.get_parameter('groq.presence_penalty').value,
            'frequency_penalty': self.get_parameter('groq.frequency_penalty').value,
            'tool_choice': self.get_parameter('groq.tool_choice').value,
        }

        if not self.api_key:
            self.get_logger().error('API Key is missing!')
            raise RuntimeError('API Key is missing')

        self.groq_client = Groq(api_key=self.api_key)
        if not self.is_network_available():
            self.get_logger().fatal('\n' + '='*50 + 
                                    '\n[NETWORK ERROR] api.groq.com is unreachable or access denied.' + 
                                    '\nPlease check your internet connection or Wi-Fi settings.' + 
                                    '\n' + '='*50)
            raise RuntimeError('Network connection failed')

        try:
            with open(self.room_file, "r") as file:
                self.rooms = yaml.safe_load(file)
        except Exception as e:
            self.get_logger().warn(f'Failed to load room file: {e}')
            self.rooms = {}

        self.tools_definition = None
        if self.groq_params['tool_choice'] != 'none' and self.function_list_file:
            try:
                if os.path.exists(self.function_list_file):
                    with open(self.function_list_file, "r") as file:
                        data = yaml.safe_load(file)
                        self.tools_definition = data.get('tools')
                        if self.tools_definition:
                            self.get_logger().info(f'Loaded {len(self.tools_definition)} tools. Mode: {self.groq_params["tool_choice"]}')
                else:
                    self.get_logger().error(f'Tools file not found: {self.function_list_file}')
            except Exception as e:
                self.get_logger().error(f'Failed to load tools file: {e}')
        
        self.add_on_set_parameters_callback(self.parameter_callback)
        self.chat_messages = {}
        self.build_prompt() 
        self.bridge = CvBridge() 

        self.action_server_ = ActionServer(
            self, ChatLlmRecognition, "groq_action",
            execute_callback=self.groq_callback, 
            callback_group=self.callback_group,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback
        )
        self.get_logger().info("\033[93mGroq Server (Enhanced Protocol) is READY.\033[0m")

    def is_network_available(self):
        try:
            self.groq_client.models.list()
            return True
        except Exception as e:
            self.get_logger().error(f"Network Check Failed: {e}")
            return False
        
    def parameter_callback(self, params):
        for param in params:
            if param.name.startswith('groq.'):
                key = param.name.replace('groq.', '')
                if key in self.groq_params:
                    self.groq_params[key] = param.value
                    self.get_logger().info(f"Updated {param.name} to {param.value}")

            elif param.name == 'api_key':
                self.api_key = param.value
                self.groq_client = Groq(api_key=self.api_key)
                self.get_logger().info("Groq API Key updated.")
            
            elif param.name == 'rooms_file':
                self.room_file = param.value
                try:
                    with open(self.room_file, "r") as file:
                        self.rooms = yaml.safe_load(file)
                    self.build_prompt()
                    self.get_logger().info(f"Rooms file reloaded from {self.room_file}")
                except Exception as e:
                    self.get_logger().error(f"Failed to reload rooms file: {e}")

            elif param.name == 'function_list_file':
                self.function_list_file = param.value
                try:
                    if os.path.exists(self.function_list_file):
                        with open(self.function_list_file, "r") as file:
                            data = yaml.safe_load(file)
                            self.tools_definition = data.get('tools')
                            self.get_logger().info(f"Tools reloaded from {self.function_list_file}")
                except Exception as e:
                    self.get_logger().error(f"Failed to reload tools file: {e}")
        return SetParametersResult(successful=True)

    def goal_callback(self, goal_request):
        self.get_logger().info('Received goal request')
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info('Received cancel request and accepted.')
        return CancelResponse.ACCEPT

    def _format_tool_call_for_api(self, tool_call_string, room_name):
        try:
            tool_data = json.loads(tool_call_string.replace("TOOL_CALL:", ""))
            tool_calls = []
            for i, cmd in enumerate(tool_data):
                tool_calls.append({
                    "id": f"call_{i}_{room_name}_{int(self.get_clock().now().nanoseconds)}",
                    "type": "function",
                    "function": {
                        "name": cmd["name"],
                        "arguments": json.dumps(cmd["args"])
                    }
                })
            return {"role": "assistant", "content": None, "tool_calls": tool_calls}
        except Exception as e:
            self.get_logger().error(f"Failed to parse tool call: {e}")
            return {"role": "assistant", "content": tool_call_string}

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
        
        for i, img_msg in enumerate(goal_handle.request.image):
            img_cv = self.bridge.imgmsg_to_cv2(img_msg, desired_encoding='bgr8')
            timestamp = self.get_clock().now().to_msg().sec
            save_name = f"captured_{timestamp}_{i}.png"
            save_path = os.path.join(self.config_path, save_name)
            try:
                cv2.imwrite(save_path, img_cv)
                self.get_logger().info(f"Image saved to: {save_path}")
            except Exception as e:
                self.get_logger().error(f"Failed to save image: {e}")

            _, buffer = cv2.imencode('.jpg', img_cv)
            b64 = base64.b64encode(buffer).decode('utf-8')
            current_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

        self.chat_messages[room].append({'role': 'user', 'content': current_content})

        feedback = ChatLlmRecognition.Feedback()
        starting_time = self.get_clock().now()

        try:
            use_tools = self.groq_params['tool_choice'] != 'none' and self.tools_definition
            
            request_params = {
                "model": goal_handle.request.model_name,
                "messages": self.chat_messages[room],
                "temperature": self.groq_params['temperature'],
                "stream": True,
                "tools": self.tools_definition if use_tools else None,
                "tool_choice": self.groq_params['tool_choice'] if use_tools else None
            }
            request_params = {k: v for k, v in request_params.items() if v is not None}

            completion = self.groq_client.chat.completions.create(**request_params)

            full_response_text = ""
            tool_calls = []

            for chunk in completion:
                if goal_handle.is_cancel_requested:
                    if self.chat_messages[room]: self.chat_messages[room].pop()
                    goal_handle.canceled()
                    return response
                
                delta = chunk.choices[0].delta
                if delta.content:
                    full_response_text += delta.content
                    feedback.wip_result = full_response_text
                    goal_handle.publish_feedback(feedback)

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        if len(tool_calls) <= tc_delta.index:
                            tool_calls.append({"id": tc_delta.id, "type": "function", "function": {"name": "", "arguments": ""}})
                        if tc_delta.function.name:
                            tool_calls[tc_delta.index]["function"]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls[tc_delta.index]["function"]["arguments"] += tc_delta.function.arguments

            if tool_calls:
                simplified_commands = [{"name": tc["function"]["name"], "args": json.loads(tc["function"]["arguments"])} for tc in tool_calls]
                response.result = f"TOOL_CALL:{json.dumps(simplified_commands)}"
                self.get_logger().info(f"\033[96mCommand Sent: {response.result}\033[0m")
            else:
                response.result = full_response_text

            if goal_handle.request.is_stack:
                if response.result.startswith("TOOL_CALL:"):
                    self.chat_messages[room].append(self._format_tool_call_for_api(response.result, room))
                else:
                    self.chat_messages[room].append({'role': 'assistant', 'content': response.result})
            else:
                self.chat_messages[room].pop()

            ending_time = self.get_clock().now()
            response.elapsed_time = (ending_time - starting_time).nanoseconds / 1e9
            self.get_logger().info(f"\033[92mFinal Result: {response.result}\033[0m")
            goal_handle.succeed()
            return response

        except Exception as e:
            self.get_logger().error(f'Groq Error: {str(e)}')
            if self.chat_messages[room]: self.chat_messages[room].pop()
            goal_handle.abort()
            return response

    def build_prompt(self):
        self.chat_messages = {}
        if not self.rooms: return 
        for room_name, history in self.rooms.items():
            self.chat_messages[str(room_name)] = []
            for talk in history:
                if "system" in talk:
                    self.chat_messages[str(room_name)].append({"role": "system", "content": talk["system"]})
                    continue
                
                elif "user" in talk:
                    text = talk["user"]
                    content = [{"type": "text", "text": text}]
                    if "files" in talk:
                        for f in talk["files"]:
                            path = f if f.startswith("/") else os.path.join(self.config_path, f)
                            if os.path.exists(path):
                                mime_type = "image/jpeg" if path.lower().endswith(('.jpg', '.jpeg')) else "image/png"
                                with open(path, "rb") as img_file:
                                    b64 = base64.b64encode(img_file.read()).decode('utf-8')
                                    content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}})
                    self.chat_messages[str(room_name)].append({"role": "user", "content": content})

                elif "model" in talk:
                    text = talk["model"]
                    if text.startswith("TOOL_CALL:"):
                        self.chat_messages[str(room_name)].append(self._format_tool_call_for_api(text, str(room_name)))
                    else:
                        self.chat_messages[str(room_name)].append({"role": "assistant", "content": text})

def main(args=None):
    rclpy.init(args=args)
    executor = MultiThreadedExecutor()
    try:
        node = GroqActionServer()
        executor.add_node(node)
        executor.spin()
    except RuntimeError:
        pass
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            if 'node' in locals():
                node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()