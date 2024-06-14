# ベースイメージを指定
FROM python:3.11-slim

# 作業ディレクトリを作成
WORKDIR /app

# 必要なパッケージをインストール
RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポートを公開
EXPOSE 8080

# 環境変数を設定
ENV FLASK_APP app/app.py

# アプリケーションを実行
#CMD ["flask", "run", "--host=0.0.0.0"]

# アプリケーションの実行コマンドを指定
CMD ["python", "app.py"]
