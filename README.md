# Studio Flávio Celso

Aplicativo de agendamento com Flask e SQLite.

## Configuração local

1. Copie `.env.example` para `.env`.
2. No arquivo `.env`, defina `FLASK_SECRET_KEY` com um valor aleatório e
   `STUDIO_INITIAL_PASSWORD` com a senha inicial desejada.
3. Instale as dependências:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Inicie o aplicativo:

   ```powershell
   python app.py
   ```

5. Acesse <http://127.0.0.1:5000>.

O banco SQLite é criado em `instance/studio.sqlite3` na primeira inicialização.
Esse diretório e o arquivo `.env` são locais e não devem ser enviados ao GitHub.
