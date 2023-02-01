import os
import sys
import glob
import json
import pandas as pd

sys.path.append(os.getcwd())

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse

import model.face.utils.face_recognition_deepface as fr
from model.pose import pose_with_mediapipe as pwm
import model.eye.gaze_tracking.gaze_tracking as gt
from model.pose.pose_with_mmpose import main
from FastAPI.utils import upload_video, download_video
from typing import List

app = FastAPI(title="HEY-I", description="This is a demo of HEY-I")

# video를 받아와야 함
# Bytes 파일로 받을지 str로 받을지 결정해야 함. 우선은 str로 받는 버전
class InferenceFace(BaseModel):
    VIDEO_PATH: str
    SAVED_DIR: str

class Item(BaseModel):
    frame_id: List[int]
    shoulder_angle: List[int]
    hands_on: List[int]


@app.get("/")
def base():
    return {"hello": "world"}


# Front에서 cloud에 저장된 원본 영상 Back에 저장
@app.post("/save_origin_video")
def save_origin_video(inp: InferenceFace):
    storage_path = inp.VIDEO_PATH
    download_path = inp.SAVED_DIR
    os.makedirs(os.path.join(*download_path.split("/")[1:-1]), exist_ok=True)
    download_video(storage_path=storage_path, download_path=download_path)
    print(f"The video was uploaded from {download_path} to {storage_path}")
    return storage_path, download_path


# Back에서 저장한 모델 예측 영상 cloud에 저장
@app.post("/upload_predict_video")
def upload_predict_video(inp: InferenceFace):
    storage_path = inp.VIDEO_PATH
    download_path = inp.SAVED_DIR
    upload_video(file_path=download_path, upload_path=storage_path)
    print(f"The video was saved from {storage_path} to {download_path}")
    return storage_path, download_path


@app.post("/face_emotion")
def get_emotion_df(inp: InferenceFace):
    VIDEO_PATH = inp.VIDEO_PATH
    SAVED_DIR = inp.SAVED_DIR
    frames = fr.video_to_frame(VIDEO_PATH, SAVED_DIR)
    emotions_mtcnn = fr.analyze_emotion(frames)
    df = fr.make_emotion_df(emotions_mtcnn)
    rec_image_list = fr.add_emotion_on_frame(emotions_mtcnn, df, SAVED_DIR)
    fr.frame_to_video(rec_image_list, VIDEO_PATH)

    df_binary = fr.make_binary_df(emotions_mtcnn, df)

    df_json = df_binary.to_json(orient="records")
    df_response = JSONResponse(json.loads(df_json))
    return df_response


@app.post("/pose_with_mmpose")
def demo_with_mmpose(inp: InferenceFace):
    VIDEO_PATH = inp.VIDEO_PATH
    SAVED_DIR = inp.SAVED_DIR
    pose_df = pd.DataFrame(main(VIDEO_PATH, SAVED_DIR))
    pose_json = pose_df.to_json(orient="records")
    pose_response = JSONResponse(json.loads(pose_json))
    return pose_response


@app.post("/eye_tracking")
def get_eye_df(inp: InferenceFace):
    gaze = gt.GazeTracking()
    VIDEO_PATH = inp.VIDEO_PATH
    SAVED_DIR = inp.SAVED_DIR
    frames = glob.glob(f"{SAVED_DIR}/*.jpg")
    frames.sort()
    df, anno_frames = gaze.analyze_eye(frames)
    df_json = df.to_json(orient="records")
    df_response = JSONResponse(json.loads(df_json))

    gaze.frame_to_video(VIDEO_PATH, anno_frames)
    return df_response
