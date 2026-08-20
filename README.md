# INBOUND PULSE

JNTO、Travel Voice、やまとごころ.jp、時事ドットコム、訪日ラボの最新トピックをまとめて確認する静的ダッシュボードです。

## 公開方法

GitHub の **Settings → Pages** で `Deploy from a branch` を選び、`main` / `(root)` を指定します。GitHub Actionsは毎日06:17（日本時間）に記事データを更新します。初回は **Actions → Update inbound topics → Run workflow** で手動実行してください。

## ローカル確認

```bash
pip install -r requirements.txt
python scripts/fetch_topics.py
python -m http.server 8000
```

記事本文は転載せず、見出し・短い要約・元記事リンクのみ保持します。取得先サイトの仕様変更により、セレクタやフィードURLの調整が必要になる場合があります。
