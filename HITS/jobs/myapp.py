from datetime import datetime, timezone
import inspect
import matplotlib.pyplot as plt
import numpy as np
# import os
import pathlib
import pickle
#import PIL
import time

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.models import Sequential

# Initialize log
print(f'This output was generated at {datetime.now(timezone.utc)} UTC\n')

# Retrieve dataset
dataset_url = "https://github.com/seub/Cheezam/raw/main/data/cheese_photos_easy.tar.gz"
data_dir = tf.keras.utils.get_file('cheese_photos_easy', origin=dataset_url, untar=True)
data_dir = pathlib.Path(data_dir)
print(f'The data_dir is: {data_dir}')
image_count = len(list(data_dir.glob('*/*.jpg'))) + len(list(data_dir.glob('*/*.jpeg')))
# print(f'Found {image_count} jpg and jpeg images.\n')

# Prepare data
batch_size = 32
img_height = 224
img_width = 224
input_shape = (img_height, img_width, 3)
train_ds = tf.keras.utils.image_dataset_from_directory(
  data_dir,
  validation_split=0.10,
  subset="training",
  seed=123,
  image_size=(img_height, img_width),
  batch_size=batch_size)
val_ds = tf.keras.utils.image_dataset_from_directory(
  data_dir,
  validation_split=0.10,
  subset="validation",
  seed=123,
  image_size=(img_height, img_width),
  batch_size=batch_size)
class_names = train_ds.class_names
num_classes = len(class_names)
print(f"Class names: {class_names}\n")

# Configure dataset for performance
AUTOTUNE = tf.data.AUTOTUNE
train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)
print(f"Dataset configured for performance.")

# Data augmentation
data_augmentation = keras.Sequential(
  [
    layers.RandomRotation(0.1, fill_mode='constant', input_shape=input_shape),
    layers.RandomZoom(0.1, fill_mode='constant'),
    layers.RandomTranslation(height_factor=0.1, width_factor=0.1, fill_mode='constant')
    #layers.RandomFlip("horizontal")
  ])
print(f"Created data augmentation layer.")

# Visualize data
plt.figure(figsize=(10, 10))
for images, labels in train_ds.take(1):
  for i in range(9):
    ax = plt.subplot(3, 3, i + 1)
    img = images[i]
    img_aug = data_augmentation(np.expand_dims(img, axis=0))[0]
    plt.imshow(img_aug.numpy().astype("uint8"))
    plt.title(class_names[labels[i]])
    plt.axis("off")
plt.savefig("output/data_sample.png")
print(f"Dataset sample written to output/data_sample.png.\n")

# Import MobileV2 model from Keras
model_dictionary = {m[0]:m[1] for m in inspect.getmembers(tf.keras.applications, inspect.isfunction)}
# print(model_dictionary.keys())
model_func = model_dictionary['MobileNetV2']
base_model = model_func(include_top=False, pooling='avg', input_shape=input_shape, weights = 'imagenet')
base_model.trainable = False
print(f"Pre-trained MobileV2 model imported from Keras.")
model = tf.keras.models.Sequential()
model.add(base_model)
model.add(tf.keras.layers.Dense(512, activation='relu'))
model.add(tf.keras.layers.Dense(num_classes))
model.compile(optimizer='adam', loss=tf.losses.SparseCategoricalCrossentropy(from_logits=True), metrics=['accuracy'])
print(f"Added two dense layers to model.")
model.summary()


# Record history function
def update_history(reset, history, model_path, epochs):
  model_path.mkdir(parents=False, exist_ok=True)
  history_path = model_path / 'training_history'
  if reset or (not history_path.is_file()):
    training_history = {'acc':[], 'val_acc':[], 'loss':[], 'val_loss':[], 'epochs':0}
  else:
    training_history = pickle.load(open(history_path, 'rb'))
  training_history['acc'] += history.history['accuracy']
  training_history['val_acc'] += history.history['val_accuracy']
  training_history['loss'] += history.history['loss']
  training_history['val_loss'] += history.history['val_loss']
  training_history['epochs'] += epochs
  with open(history_path, 'wb') as file_pi:
    pickle.dump(training_history, file_pi)
  return training_history

# Visualize history function
def visualize_training(training_history):
  epochs_range = range(1, 1+training_history['epochs'])
  plt.figure(figsize=(10, 10))
  plt.xticks(epochs_range)
  plt.plot(epochs_range, training_history['acc'], label='Training Accuracy')
  plt.plot(epochs_range, training_history['val_acc'], label='Validation Accuracy')
  plt.ylim(bottom=0)
  plt.legend(loc='lower right')
  plt.title('Training and Validation Accuracy')
  plt.savefig("output/training_history.png")

# Visualize computation time
class timecallback(tf.keras.callbacks.Callback):
  def __init__(self):
    self.times = []
    self.time_begin = time.perf_counter()
  def on_epoch_end(self,epoch,logs = {}):
    self.time_end = time.perf_counter()
    self.times.append(self.time_end - self.time_begin)
    self.time_begin = self.time_end
  def on_train_end(self,logs = {}):
    plt.figure(figsize=(10, 10))
    plt.xlabel('Epoch')
    plt.ylabel('Time (seconds)')
    xticks = range(1, 1+len(self.times))
    plt.xticks(xticks)
    plt.plot(xticks, self.times)
    plt.ylim(bottom=0)
    plt.savefig('output/epochs_time.png')

# Train model
epochs = 15
model_path = pathlib.Path.home() / '.keras/models/MobileV2'
reset = True
if reset==False:
  assert model_path.is_dir()
time_begin = time.perf_counter()
timetaken = timecallback()
history = model.fit(train_ds, validation_data=val_ds, epochs=epochs, verbose=0, callbacks=[timetaken])
time_end = time.perf_counter()
print("Total time spent training: {:.2f} seconds".format(time_end-time_begin))
training_history = update_history(reset=reset, history=history, model_path=model_path, epochs=epochs)
visualize_training(training_history)
print(f"Number of epochs: {epochs}")
print(f"Final training accuracy: {training_history['acc'][-1]}")
print(f"Final validation accuracy: {training_history['val_acc'][-1]}")