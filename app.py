import gradio as gr
import cv2
import torch
import numpy as np
import tensorflow as tf
import requests

### GRADIO INTERFACE WITH PREDICTION CAM / GRADCAM / SALIENCY MAPS

inception_net = tf.keras.applications.MobileNetV2()


# Download human-readable labels for ImageNet.
response = requests.get("https://git.io/JJkYN")
labels = response.text.split("\n")

def classify_image(input, model, segm, label):
  input = input.reshape((-1, 224, 224, 3))
  if segm:
    input = input
  if model == 'MobilenetV2':
    input = tf.keras.applications.mobilenet_v2.preprocess_input(input)
  elif model == 'InceptionV3':
    input = tf.keras.applications.mobilenet_v2.preprocess_input(input)
  elif model == 'InceptionResnet':
    input = tf.keras.applications.mobilenet_v2.preprocess_input(input)
  prediction = inception_net.predict(input).flatten()
  confidences = {labels[i]: float(prediction[i]) for i in range(1000)}
  return confidences


demo = gr.Interface(
            fn=classify_image, 
            inputs=[
              gr.Image(shape=(224, 224)),
              gr.Textbox(value='Apple Healthy', label='label'),
              gr.Dropdown(choices=['MobilenetV2','InceptionV3','InceptionResnet'], type="value", default='InceptionV3', label='model'),
              gr.Checkbox(label="Remove Background ?"),
              ],
            outputs=gr.Label(num_top_classes=3),
            examples=[
              ["Test/Plant_leave_diseases_dataset_without_augmentation/Apple___healthy/image (1).JPG", 'Apple Healthy'],
              ["Test/Plant_leave_diseases_dataset_without_augmentation/Grape___Esca_(Black_Measles)/image (15).JPG", 'Grape Black Measles'],
              ["Test/Plant_leave_diseases_dataset_without_augmentation/Cherry___Powdery_mildew/image (21).JPG", 'Cherry Powdery mildew'],
              ["Test/Plant_leave_diseases_dataset_without_augmentation/Pepper,_bell___Bacterial_spot/image (25).JPG", 'Bell Pepper Bacterial_spot'],
              ["Test/Plant_leave_diseases_dataset_without_augmentation/Strawberry___Leaf_scorch/image (14).JPG", 'Strawberry Leaf_scorch'],
              ],
            interpretation="shap",
            num_shap=3,
            title='Crop Disease Detection'
        )

if __name__ == "__main__":
    demo.launch()


