<a name="readme-top"></a>

[JA](README.md) | [EN](README_en.md)

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]


# Groq ROS

<details>
  <summary>目次</summary>
  <ol>
    <li>
      <a href="#概要">概要</a>
    </li>
    <li>
      <a href="#セットアップ">セットアップ</a>
      <ul>
        <li><a href="#環境条件">環境条件</a></li>
        <li><a href="#インストール方法">インストール方法</a></li>
      </ul>
    </li>
    <li><a href="#実行操作方法">実行・操作方法</a></li>
    <li><a href="#サーバーへのリクエストの送信">サーバーへのリクエストの送信</a></li>
    <li><a href="#マイルストーン">マイルストーン</a></li>
    <li><a href="#参考文献">参考文献</a></li>
  </ol>
</details>

## 概要

`Groq ROS`は，Groq APIと連携して，ROS2上で大規模言語モデル（LLM）とのチャット機能を提供するパッケージです．画像やテキストをLLMへの入力として使用することも可能です．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

## セットアップ

ここで，本レポジトリのセットアップ方法について説明します．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

### 環境条件

まず，以下の環境を整えてから，次のインストール段階に進んでください．

| System  | Version |
| --- | --- |
| Ubuntu | 22.04 (Jammy Jellyfish) |
| ROS    | Humble Hawksbill |
| Python | 3.10 |

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>


### インストール方法


1. ROSの`src`フォルダに移動します．
```sh
$ cd ~/colcon_ws/src/
```

2. 本レポジトリをcloneします．
```sh
$ git clone https://github.com/TeamSOBITS/groq_ros
```

3. レポジトリの中へ移動します．
```sh
$ cd groq_ros/
```

4. 依存パッケージをインストールします．
```sh
$ bash install.sh
```

5. パッケージをコンパイルします．
```sh
$ cd ~/colcon_ws/
$ colcon build --symlink-install
$ source ~/colcon_ws/install/setup.sh
```

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>


## 実行・操作方法

1. Groq APIキーをターミナル上で設定します．
    ```sh
    export GROQ_API_KEY=************
    ```

> [!NOTE]
> Groq APIキーを獲得するために，こちらのサイトを参照してください．
> https://console.groq.com/keys

2. [groq_config.yaml](./config/groq_config.yaml)上でモデルの設定を用途に応じて更新してください．
    ```yaml
    groq:
      temperature: 0.5  # 回答のランダム性（創造性）を制御．値が低いほど確実性の高い単語を選び（論理的・決定的），高いほど意外性のある単語を選ぶ
      json_mode: false  # 出力フォーマットを強制的にJSON形式にするかどうか
      max_tokens: 4096  # 1回の生成でAIが出力できるトークンの最大値
      top_p: 1.0  # 単語を選ぶ際，累積確率が p に達する上位の候補からのみ選択．1.0 はすべての候補を対象にします．0.1 にすると，上位10%の確率を持つ「非常に無難な単語」しか選ばれなくなる
      seed: -1  # 生成の再現性を確保するための乱数シード値．-1 はシードを指定せず，毎回ランダムに生成       
      presence_penalty: 0.6 # 値を大きくすると新しいトピックを出力しやすくなる                 
      frequency_penalty: 0.3  # 値を大きくすると同じ言葉の繰り返しが抑制        
    ```

3. [任意] [groq_room.yaml](./config/groq_room.yaml)上で，文脈エンジニアリングのためのルームを記述してください．
    ```yaml
    # 例：自チームに関する紹介のチャットボット
    team_introduce:               # team_introduceという別の部屋も準備している
      - {user : "私達のチームはSOBITSという学生チームを組んでいます！"}  # imageを入れない場合＝LLM
      - {model: "SOBITSという学生チームを組んでいるのですね！素晴らしいですね！どういったチームなのですか？"}
      - {user : "学部生・修士・博士と幅広く在籍し，40人います！"}
      - {model: "40人ものメンバーがいる大規模な学生チームなのですね！\n幅広い層の方が在籍されているとのこと，多様な視点や知識が集まって素晴らしいチームになりそうですね．"}
    ```

4. Groq ROSのアクションサーバを起動します．
    ```sh
    ros2 launch groq_ros groq_server.launch.py
    ```

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>


### サーバーへのリクエストの送信

`sobits_interfaces/action/ChatLlmRecognition`というアクションを用いて，Groqサーバにリクエストを送信します．

| 項目              | フィールド名          | 型                     | 説明                                                |
| :---------------- | :-------------------- | :--------------------- | :-------------------------------------------------- |
| **アクション名**  |                       |                        | `groq_action`                                     |
| **Goal**          | `room_name`           | string                 | 会話履歴を管理するための任意のルームの名前          |
|                   | `request`             | string                 | ユーザーからのテキストメッセージ                    |
|                   | `image`               | sensor_msgs/Image[]    | 送信する画像メッセージのリスト                      |
|                   | `sound_file_path`     | string[]               | 送信する音声ファイルのパスのリスト                  |
|                   | `model_name`          | string                 | 使用するGroqモデルの名前 (例: "openai/gpt-oss-120b") |
|                   | `is_stack`            | bool                   | 現在の会話を会話履歴にスタックするかどうか          |
| **Result**        | `result`              | string                 | Groqからの応答テキスト                            |

---
使用可能なモデル一覧は[groq_ros/model_list.py](groq_ros/model_list.py)を実行して確認してください．


<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

<!-- マイルストーン -->
## マイルストーン

現時点のバッグや新規機能の依頼を確認するために[Issueページ](issues-url) をご覧ください．

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>

## 参考文献
* [Groq](https://groq.com/)

<p align="right">(<a href="#readme-top">上に戻る</a>)</p>


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
