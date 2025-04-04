from openai import OpenAI
import os
import io
import requests
from django.core.files.storage import default_storage
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.conf import settings
from azure.storage.blob import BlobServiceClient
from django.conf import settings
from datetime import datetime

@api_view(['POST'])
def transcribe_audio(request):
    print("Request FILES:", request.FILES)
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({"error": "音声ファイルがありません"}, status=400)

    # media フォルダがなければ作成
    media_dir = "media"
    if not os.path.exists(media_dir):
        os.makedirs(media_dir)

    # InMemoryUploadedFile を BytesIO に変換
    audio_bytes = io.BytesIO(audio_file.read())
    audio_bytes.name = "audio.webm"

    print("音声ファイルを文字起こし中...")

    # Whisper API を使用して文字起こし
    whisper_response = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_bytes
    )
    text = whisper_response.text

    print("文字起こし完了")
    print(f"文字起こし結果: {text}")
    print("GPT-4 で返答生成中...")

    # GPT-4 で返答生成
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": text}]
    )
    gpt_response = response.choices[0].message.content

    print("返答生成完了")
    print(f"返答: {gpt_response}")
    print("音声合成中...")

    # にじボイス（または VOICEVOX）で音声合成
    voice_data = synthesize_voice(gpt_response)

    print("音声合成完了")
    
    # 音声ファイルとして保存
    # audio_path = "media/response.wav"
    try:
        # with open(audio_path, "wb") as f:
        #     f.write(voice_data)
        
        # if os.path.exists(audio_path):
        #     file_size = os.path.getsize(audio_path)
        #     print(f"ファイル正常保存: {audio_path}, サイズ: {file_size} バイト")
        # else:
        #     print(f"警告: ファイルが保存されていません: {audio_path}")
        #     return Response({"text": gpt_response, "error": "ファイル保存失敗"}, status=500)

        # audio_url = request.build_absolute_uri("/media/response.wav")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = f"response_{timestamp}.wav"

        # Azure Blob にアップロード
        audio_url = upload_to_azure_blob(voice_data, filename)

        return Response({"text": gpt_response, "audio_url": audio_url})
    except Exception as e:
        print(f"ファイル保存エラー: {str(e)}")
        return Response({"text": gpt_response, "error": f"音声ファイルの保存に失敗しました: {str(e)}"}, status=500)


def synthesize_voice(text):
    # 環境変数からAPIキーを取得
    api_key = os.getenv("NIJI_VOICE_API_KEY")
    if not api_key:
        print("エラー: APIキーが設定されていません。")
        return

    # 取得したボイスIDを設定
    voice_actor_id = "544f6937-f2cd-4fde-a094-a1d612071be3"
    url = f"https://api.nijivoice.com/api/platform/v1/voice-actors/{voice_actor_id}/generate-voice"

    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    data = {"script": text, "speed": "0.8", "format": "wav"}

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        audio_url = response.json()["generatedVoice"]["audioFileUrl"]
        audio_response = requests.get(audio_url)
        audio_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"エラーが発生しました: {e}")
    return audio_response.content

# 音声のblob保存
def upload_to_azure_blob(file_data: bytes, filename: str) -> str:
    connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
    container_name = settings.AZURE_CONTAINER_NAME
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)

    blob_client.upload_blob(file_data, overwrite=True)

    blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{filename}"
    return blob_url