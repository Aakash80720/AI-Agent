from transformers import pipeline
import gradio as gr

summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
translator = pipeline("translation_en_to_fr", model="Helsinki-NLP/opus-mt-en-fr")
classifier = pipeline("sentiment-analysis")

def summarize(message: str, history) -> str:
    """Summarize the input text using a pre-trained model."""
    if len(message) < 50:
        return "Text too short to summarize."
    return summarizer(message)[0]["summary_text"]

def translate(message: str, history) -> str:
    """Translate the input text from English to French using a pre-trained model."""
    return translator(message)[0]["translation_text"]

def classify(message: str, history) -> str:
    """Classify the sentiment of the input text using a pre-trained model."""
    return classifier(message)[0]["label"]

gr_summarize = gr.ChatInterface(
    fn=summarize,
    title="Text Summarization",
    description="Summarize the input text using a pre-trained model."
)
gr_translate = gr.ChatInterface(
    fn=translate,
    title="Text Translation",
    description="Translate the input text from English to French using a pre-trained model."
)
gr_classify = gr.ChatInterface(
    fn=classify,
    title="Sentiment Analysis",
    description="Classify the sentiment of the input text using a pre-trained model."
)
with gr.Blocks() as demo:
    gr.Markdown("# Gradio a HuggingFace MCP Server Example")
    gr.Markdown("This demo showcases text summarization, translation, and sentiment analysis using HuggingFace models.")
    gr.Markdown("Choose a task from the sidebar to get started.")
    
    with gr.Tab("Summarization"):
        gr_summarize.render()
    
    with gr.Tab("Translation"):
        gr_translate.render()
    
    with gr.Tab("Sentiment Analysis"):
        gr_classify.render()

demo.launch(mcp_server=True)