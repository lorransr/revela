FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl libheif-examples tzdata libgl1 libegl1 libgles2 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.15.0 torchvision==0.29.2
RUN pip install --no-cache-dir icloudpd==1.34.0 pillow==13.0.0 fastapi==0.165.0 uvicorn==0.54.0 jinja2==3.1.6 \
      img2pdf==0.6.3 mediapipe==1.2.3 open_clip_torch==4.2.2

# The models come in at build time: the containers that read photos run without network.
ENV HF_HOME=/models HF_HUB_OFFLINE=1
RUN mkdir -p /models \
 && HF_HUB_OFFLINE=0 python -c "import open_clip; open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')" \
 && curl -fsSL -o /models/aesthetic.pth https://github.com/LAION-AI/aesthetic-predictor/raw/main/sa_0_4_vit_b_32_linear.pth \
 && curl -fsSL -o /models/face_landmarker.task \
      https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task \
 && echo "c7b14cead230694acc7b9447974d3cad78003c72da032e402a303b6c2429e85f  /models/aesthetic.pth" | sha256sum -c - \
 && echo "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff  /models/face_landmarker.task" | sha256sum -c - \
 && chmod -R a+rX /models

COPY sync.sh /usr/local/bin/revela-sync
COPY *.py /app/
COPY templates /app/templates
RUN ln -s /app/revela.py /usr/local/bin/revela
