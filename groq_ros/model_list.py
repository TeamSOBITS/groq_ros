import os
import rclpy
from rclpy.node import Node
from groq import Groq

class GroqModelList(Node):
    def __init__(self):
        super().__init__('groq_model_list_node')
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            self.get_logger().error("GROQ_API_KEY is not set in environment variables.")
            return
            
        self.client = Groq(api_key=api_key)
        self.get_groq_models()

    def get_groq_models(self):
        try:
            models = self.client.models.list()
            self.get_logger().info(f"\n{'Model ID':<40} | {'Owned By':<10}")
            self.get_logger().info("-" * 55)
            
            for model in sorted(models.data, key=lambda x: x.id):
                print(f"{model.id:<40} | {model.owned_by:<10}")
        except Exception as e:
            self.get_logger().error(f"Error occurred: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = GroqModelList()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()