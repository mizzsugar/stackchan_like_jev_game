話しかけると表情が変わるロボットのミニゲームです。Pyxel1画面で完結し、入力内容は
[Jev](https://www.typesafe.ai/)（TypeSafe AIの`system_one` API）で5パターンに分類して、
ロボットの表情に反映します。

[game_play.webm](https://github.com/user-attachments/assets/aec15698-98ec-458f-b71f-c014bf625430)



## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- TypeSafe AI の API キー（[console.typesafe.ai](https://console.typesafe.ai/settings/keys)）

## Setup & Run

```bash
uv sync
export TYPESAFE_API_KEY="your-api-key"   # PowerShellなら $env:TYPESAFE_API_KEY = "..."
uv run face_game.py
```

初回実行時に `uv` が `pyxel` / `typesafe-sdk` を自動で解決・インストールします
(`--no-project` を付けると既存の `pyproject.toml` の影響を受けずに実行できます)。

`TYPESAFE_API_KEY` 未設定・通信失敗時は例外を出さず常に `nod`(通常表情)にフォールバックするので、
キー無しでも起動確認だけは可能です。

## 遊び方

| キー | 動作 |
|---|---|
| `SPACE` / `ENTER`（待機中） | 入力モードに入る |
| 任意の文字キー | 画面下の入力欄に文字を追加（英数字・一般的な記号、Shiftで大文字/記号） |
| `BACKSPACE` | 1文字削除（長押しでリピート） |
| `ENTER`（入力中） | 入力を確定してJevに送信 → 表情が変わる |
| `ESC`（入力中） | 入力をキャンセルして待機状態に戻る |
| `Q` / `ESC`（待機中） | ゲーム終了 |

入力は英語のみ対応です（IME/日本語入力は非対応）。最大42文字まで、それ以上は表示欄で
末尾側にスクロールします。

### 反応と表情の対応

| 反応 | 表情 | 発生条件(Jevへの指示) |
|---|---|---|
| `smile` | 喜 (joy) | 褒め言葉や嬉しいこと |
| `angry` | 怒 (anger) | 愚痴・文句・悪口 |
| `cry` | 哀 (sorrow) | 悲しい話・辛い話 |
| `lol` | 楽 (fun) ＋震えモーション | とても面白い話・強烈な冗談 |
| `nod` | 通常 (normal) ＋うなずきモーション | 上記のどれにも当てはまらない場合 |

判定基準は `REACTION_CRITERIA`、対応表は `REACTION_TO_EXPR` にあるので、書き換えれば
挙動を調整できます。

## Notes

- 画面は `pyxel.init(..., display_scale=2)` で400x400固定。倍率を変えたい場合はこの値を編集してください。
- 見た目のパーツ座標・描画ロジックは元の「表情チェンジロボット」から流用しています。
- `quit_key` は手動管理しているため、入力中の `ESC` はゲーム終了ではなくキャンセルとして働きます。
