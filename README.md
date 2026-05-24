# 🌍 CityScope

Aplicação web em Flask que mostra informações sobre países e cidades — bandeira, capital, população, moeda (com conversão para USD), idiomas, hora local, mapa e clima (atual, histórico ou previsão de 7 dias).

## 📁 Estrutura do projeto

Para o Flask funcionar, organize os arquivos **exatamente** assim:

```
cityscope/
├── app.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── README.md
├── .gitignore
├── templates/
│   └── index.html
└── static/
    └── style.css
```

> ⚠️ O arquivo `index.html` **precisa** estar dentro da pasta `templates/` e o `style.css` dentro de `static/`. O Flask procura os arquivos nesses lugares por padrão.

## 🚀 Como rodar localmente

1. Clone o repositório:
   ```bash
   git clone https://github.com/SEU-USUARIO/cityscope.git
   cd cityscope
   ```

2. Crie um ambiente virtual e instale as dependências:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Linux / macOS
   venv\Scripts\activate           # Windows
   pip install -r requirements.txt
   ```

3. Execute a aplicação:
   ```bash
   python app.py
   ```

4. Abra <http://127.0.0.1:5000> no navegador.

## ☁️ Deploy a partir do GitHub

O GitHub **não executa** apps Flask (GitHub Pages serve só conteúdo estático). Conecte seu repositório a um destes serviços gratuitos:

### Render (recomendado)

1. Faça login em <https://render.com> com sua conta do GitHub.
2. Clique em **New +** → **Web Service**.
3. Selecione seu repositório `cityscope`.
4. Configure:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Clique em **Create Web Service**. O Render detecta o `Procfile` automaticamente e expõe a URL pública.

### Railway

1. Acesse <https://railway.app> → **Deploy from GitHub repo**.
2. Escolha o repositório — a detecção é automática via `Procfile` e `requirements.txt`.

### PythonAnywhere

Suporta Flask no plano gratuito; importação manual do repositório via console Bash.

## 🔌 APIs utilizadas

- [REST Countries](https://restcountries.com) — dados dos países
- [Open-Meteo](https://open-meteo.com) — clima atual, histórico e previsão
- [OpenStreetMap](https://www.openstreetmap.org) — mapa embed

## 👥 Autores

Aina Pascual López & Henrique Passoni
