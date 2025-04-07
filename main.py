from app import create_app
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env

app = create_app()  # Panggil fungsi create_app() dari __init__.py

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
