# Leopoldina Digital

Plataforma digital governamental para cidadãos registrarem ocorrências urbanas e secretarias acompanharem a resolução.

## 🚀 Tecnologias
- **Backend**: Python, FastAPI, SQLAlchemy
- **Banco de Dados**: SQLite (para desenvolvimento local), preparado para PostgreSQL
- **Frontend**: HTML5, CSS3, JS Vanilla (Hospedado via Firebase Hosting)
- **IA**: Integração com OpenAI API (Mock configurável)

## 📋 Como Rodar Localmente

### 1. Iniciar o Backend
Abra um terminal na pasta do projeto e navegue até `backend`:
```bash
cd Leopoldina.D/backend
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
O backend estará rodando em `http://localhost:8000`.

A API gerará o arquivo do banco SQLite automaticamente ao inciar.

### 2. Iniciar o Frontend (Live Server)
Abra a pasta `Leopoldina.D/frontend` no VSCode e inicie com a extensão **Live Server**, ou rode via bash:
```bash
cd Leopoldina.D/frontend
npx http-server . -p 5500
```
Acesse `http://localhost:5500`.

## ☁️ Como Fazer o Deploy no Firebase

1. Acesse https://console.firebase.google.com e crie um projeto (ex: `leopoldina-digital`).
2. Instale o CLI do Firebase no seu computador:
   ```bash
   npm install -g firebase-tools
   ```
3. Autentique-se e inicialize dentro da raiz do projeto (`Leopoldina.D`):
   ```bash
   firebase login
   firebase init hosting
   ```
   *Selecione a pasta `frontend` quando perguntado qual será o diretório público.*
4. Faça o deploy:
   ```bash
   firebase deploy --only hosting
   ```

## ⚙️ Configurações e IA
No diretório `backend`, edite o arquivo `.env` para colocar a chave real do ChatGPT (OpenAI API), caso queira que o chatbot no site retorne respostas de IA verdadeiras (hoje ele usa um fallback automático se não houver chave).
