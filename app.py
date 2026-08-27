from email.mime.text import MIMEText
import os
import openai
import time
import streamlit as st
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from src.config.mlflow_config import MetricsCollector
from src.model.retrive_azure_index import search_azure_index
from src.model.system_prompt import create_system_prompt
from src.model.get_model_response import get_openai_response
from src.evaluation.user_question_bias import check_bias_in_user_question
from src.evaluation.model_response_bias import check_bias_in_model_response
from src.evaluation.answer_validation import key_concept_match 
from src.model.alerts import send_slack_alert
# Load environment variables from .env file
load_dotenv()
collector = MetricsCollector()


def main():
    st.set_page_config(page_title="AskRC", page_icon="🎓")
    st.header("AskRC 🎓")

    user_question = st.text_input("Ask a Question")

    if st.button("Get Answer"):
        with st.spinner("Processing..."):
            # Trigger the Airflow DAG
            #trigger_airflow_dag(user_question)
            # Step 1: Check for bias in the user question
            user_question_clean, bias_message = check_bias_in_user_question(user_question)
            
            if bias_message:
                # Display rephrase suggestion if bias is detected
                st.warning(bias_message)
                #send_email_alert("Bias detected in user question", f"The user question contains bias: {user_question_clean}. Bias message: {bias_message}")
            else:
                # Step 2: Retrieve context from Azure Search
                context = search_azure_index(user_question_clean)
                
                # Step 3: Create the system prompt
                system_prompt = create_system_prompt(context, user_question_clean)
                
                # Step 4: Get response from OpenAI API
                answer = get_openai_response(system_prompt)
                
                # Step 5: Check for bias in the model response
                answer_clean, response_bias_message = check_bias_in_model_response(answer)
                
                # Step 6: Validate answer relevance using key concept match
                if key_concept_match(answer_clean, context):
                    st.write(answer_clean)
                    if response_bias_message:
                        st.warning(response_bias_message)
                        send_slack_alert("Bias detected in model response", f"Bias message in the model response: {response_bias_message}")
                    else:
                        st.success("Answer provided.")
                else:
                    st.warning("The question lacks sufficient contextual relevance.")
                    send_slack_alert("Question lacks context", f"The question provided lacks sufficient contextual relevance: {answer_clean}")

# Run the app
if __name__ == "__main__":
    main()
    collector.log_all()

#mlflow server --host 127.0.0.1 --port 8080