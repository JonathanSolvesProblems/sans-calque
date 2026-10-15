FROM python:3.12-slim

WORKDIR /srv
# CPU-only torch first: the default Linux wheel pulls CUDA (several GB) and the host has <8 GB free.
# The app never runs a model locally; tinker-cookbook just imports torch.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt

COPY app/ app/
COPY scripts/translate.py scripts/termium.py scripts/
COPY data/termium_index.json data/acronym_map.json data/bilingual_acronyms.json data/
COPY results/ results/

ENV PYTHONUNBUFFERED=1 HF_HOME=/cache/hf
EXPOSE 8000
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
