import tensorflow as tf

converter = tf.lite.TFLiteConverter.from_saved_model("model2")  # path to the SavedModel directory
converter.optimizations = [tf.lite.Optimize.DEFAULT]
# # This enables quantization
# converter.optimizations = [tf.lite.Optimize.DEFAULT]
# # This sets the representative dataset for quantization
# converter.representative_dataset = representative_data_gen
# # This ensures that if any ops can't be quantized, the converter throws an error
# converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
# # For full integer quantization, though supported types defaults to int8 only, we explicitly declare it for clarity.
# converter.target_spec.supported_types = [tf.int8]
# # These set the input and output tensors to uint8 (added in r2.3)
# converter.inference_input_type = tf.uint8
# converter.inference_output_type = tf.uint8
tflite_model = converter.convert()

# Save the model.
with open('model_quant.tflite', 'wb') as f:
    f.write(tflite_model)

print("Model converted")
