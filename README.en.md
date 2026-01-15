<a name="readme-top"></a>

[JA](README.md) | [EN](README_en.md)

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]


# Groq ROS

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#introduction">Introduction</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#launch-and-usage">Launch and Usage</a></li>
    <li><a href="#sending-requests-to-the-server">Sending Requests to the Server</a></li>
    <li><a href="#milestone">Milestone</a></li>
    <li><a href="#references">References</a></li>
  </ol>
</details>

## Introduction

`Groq ROS` is a package that integrates with the Groq API to provide chat functionality with Large Language Models (LLMs) on ROS 2. It also supports using both images and text as inputs for the LLM.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

This section describes how to set up this repository.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Prerequisites

First, ensure you have the following environment set up before proceeding with the installation.

| System  | Version |
| --- | --- |
| Ubuntu | 22.04 (Jammy Jellyfish) |
| ROS    | Humble Hawksbill |
| Python | 3.10 |

<p align="right">(<a href="#readme-top">back to top</a>)</p>


### Installation


1. Navigate to your ROS2 src folder．
```sh
$ cd ~/colcon_ws/src/
```

2. Clone this repository．
```sh
$ git clone https://github.com/TeamSOBITS/groq_ros
```

3. Move into the repository directory.
```sh
$ cd groq_ros/
```

4. Install dependent package.
```sh
$ bash install.sh
```

5. Compile the package.
```sh
$ cd ~/colcon_ws/
$ colcon build --symlink-install
$ source ~/colcon_ws/install/setup.sh
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Launch and Usage

1. Set the Groq API key in the terminal.
    ```sh
    export GROQ_API_KEY=************
    ```

> [!NOTE]
> To obtain a Groq API key, please refer to the following site:
> https://console.groq.com/keys

2. Update the model settings in [groq_config.yaml](./config/groq_config.yaml) according to your needs.
    ```yaml
    groq:
          temperature: 1.0  # Controls randomness (creativity). Lower values result in more deterministic/logical output, while higher values lead to more creative/varied responses. Range: 0.0 - 2.0.
          json_mode: false  # Whether to force the model to output in JSON format.
          max_tokens: 4096  # The maximum number of tokens the AI can generate in a single response.
          top_p: 1.0        # Nucleus sampling: The model considers only the tokens with top_p probability mass. 1.0 includes all tokens, while 0.1 considers only the top 10% most likely tokens. Range: 0.0 - 1.0.
          seed: -1          # Random seed for reproducibility. Set to -1 for random generation (no fixed seed).
          presence_penalty: 0.0 # Higher values encourage the model to talk about new topics. Range: -2.0 - 2.0.
          frequency_penalty: 0.0 # Higher values discourage the model from repeating the same words/phrases. Range: -2.0 - 2.0.
    ```

3. [Optional] Configure a room for context engineering in [groq_room.yaml](./config/groq_room.yaml).
    ```yaml
      example_room: # Room name
        # system: Define the AI's personality and constraints (role, tone, rules)
        - {system: "You are the guidance robot 'SOBIT'. Please respond in polite Japanese."}

        # user: Human (user) input (images can be attached using 'files')
        - {user: "Hello! What can you do?", files: ["sobit_mini.png"]}

        # model: AI responses (used to maintain conversation flow)
        - {model: "Hello! I am SOBIT. I can provide facility guidance and image recognition."}
    ```

    ```yaml
      # Example: Chatbot introducing our team
      team_introduce:               # Preparing a separate room called team_introduce
        - {user : "Our team is a student team called SOBITS!"}  # If no image is included = LLM
        - {model: "So you formed a student team called SOBITS! That's wonderful! What kind of team is it?"}
        - {user : "We have 40 members, ranging from undergraduates to masters and PhDs!"}
        - {model: "A large student team with 40 members! With such a wide range of members, it sounds like a wonderful team with diverse perspectives and knowledge gathered together."}
    ```

4. Launch the Groq ROS action server.
    ```sh
    ros2 launch groq_ros groq_server.launch.py
    ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>


### Sending Requests to the Server
Send a request to the Groq server using the action `sobits_interfaces/action/ChatLlmRecognition`.

| Item              | Field Name            | Type                   | Description                                         |
| :---------------- | :-------------------- | :--------------------- | :-------------------------------------------------- |
| **Action Name**   |                       |                        | `groq_action`                                     |
| **Goal**          | `room_name`           | string                 | Arbitrary room name for managing conversation history |
|                   | `request`             | string                 | Text message from the user                          |
|                   | `image`               | sensor_msgs/Image[]    | List of image messages to send                      |
|                   | `sound_file_path`     | string[]               | List of paths to files to send                |
|                   | `model_name`          | string                 | Name of the Groq model to use (e.g., "openai/gpt-oss-120b") |
|                   | `is_stack`            | bool                   | Whether to stack the current conversation in the conversation history |
| **Result**        | `result`              | string                 | Response text from Groq                           | 

---
- You can check the list of available models using the following command:

```sh
ros2 run groq_ros groq_model_list

```

> [!NOTE]
> Currently, **groq_ros** does not support audio input (Speech-to-Text) or audio output (Text-to-Speech). These features are under consideration for future updates.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- マイルストーン -->
## Milestone

See the [open issues]([issues-url]) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## References
* [Groq](https://groq.com/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/TeamSOBITS/groq_ros.svg?style=for-the-badge
[contributors-url]: https://github.com/TeamSOBITS/groq_ros/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/TeamSOBITS/groq_ros.svg?style=for-the-badge
[forks-url]: https://github.com/TeamSOBITS/groq_ros/network/members
[stars-shield]: https://img.shields.io/github/stars/TeamSOBITS/groq_ros.svg?style=for-the-badge
[stars-url]: https://github.com/TeamSOBITS/groq_ros/stargazers
[issues-shield]: https://img.shields.io/github/issues/TeamSOBITS/groq_ros.svg?style=for-the-badge
[issues-url]: https://github.com/TeamSOBITS/groq_ros/issues
[license-shield]: https://img.shields.io/github/license/TeamSOBITS/groq_ros.svg?style=for-the-badge
[license-url]: LICENSE
