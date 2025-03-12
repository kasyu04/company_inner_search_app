"""
このファイルは、Webアプリのメイン処理が記述されたファイルです。
"""

############################################################
# 1. ライブラリの読み込み
############################################################
# 「.env」ファイルから環境変数を読み込むための関数
from dotenv import load_dotenv
# ログ出力を行うためのモジュール
import logging
# streamlitアプリの表示を担当するモジュール
import streamlit as st
# （自作）画面表示以外の様々な関数が定義されているモジュール
import utils
# （自作）アプリ起動時に実行される初期化処理が記述された関数
from initialize import initialize
# （自作）画面表示系の関数が定義されているモジュール
import components as cn
# （自作）変数（定数）がまとめて定義・管理されているモジュール
import constants as ct
# pandasをインポート
import pandas as pd
# osモジュールをインポート
import os
# langchain関連のモジュール
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader, TextLoader
from langchain_community.document_loaders.csv_loader import CSVLoader


############################################################
# 2. 設定関連
############################################################
# ブラウザタブの表示文言を設定
st.set_page_config(
    page_title=ct.APP_NAME
)

# 環境変数を読み込む
load_dotenv()

# ログ出力を行うためのロガーの設定
logger = logging.getLogger(ct.LOGGER_NAME)


############################################################
# 3. 初期化処理
############################################################
try:
    # 初期化処理（「initialize.py」の「initialize」関数を実行）
    initialize()
except Exception as e:
    # エラーログの出力
    logger.error(f"{ct.INITIALIZE_ERROR_MESSAGE}\n{e}")
    # エラーメッセージの画面表示
    st.error(utils.build_error_message(ct.INITIALIZE_ERROR_MESSAGE), icon=ct.ERROR_ICON)
    # 後続の処理を中断
    st.stop()

# アプリ起動時のログファイルへの出力
if not "initialized" in st.session_state:
    st.session_state.initialized = True
    logger.info(ct.APP_BOOT_MESSAGE)


############################################################
# 4. 初期表示
############################################################
# タイトル表示
cn.display_app_title()

# モード表示
cn.display_select_mode()

# AIメッセージの初期表示
cn.display_initial_ai_message()


############################################################
# 5. 会話ログの表示
############################################################
try:
    # 会話ログの表示
    cn.display_conversation_log()
except Exception as e:
    # エラーログの出力
    logger.error(f"{ct.CONVERSATION_LOG_ERROR_MESSAGE}\n{e}")
    # エラーメッセージの画面表示
    st.error(utils.build_error_message(ct.CONVERSATION_LOG_ERROR_MESSAGE), icon=ct.ERROR_ICON)
    # 後続の処理を中断
    st.stop()


############################################################
# 6. チャット入力の受け付け
############################################################
chat_message = st.chat_input(ct.CHAT_INPUT_HELPER_TEXT)


############################################################
# 7. チャット送信時の処理
############################################################
if chat_message:
    # ==========================================
    # 7-1. ユーザーメッセージの表示
    # ==========================================
    # ユーザーメッセージのログ出力
    logger.info({"message": chat_message, "application_mode": st.session_state.mode})

    # ユーザーメッセージを表示
    with st.chat_message("user"):
        st.markdown(chat_message)

    # ==========================================
    # 7-2. LLMからの回答取得
    # ==========================================
    # 「st.spinner」でグルグル回っている間、表示の不具合が発生しないよう空のエリアを表示
    res_box = st.empty()
    # LLMによる回答生成（回答生成が完了するまでグルグル回す）
    with st.spinner(ct.SPINNER_TEXT):
        try:
            # 画面読み込み時に作成したRetrieverを使い、Chainを実行
            llm_response = utils.get_llm_response(chat_message)
        except Exception as e:
            # エラーログの出力
            logger.error(f"{ct.GET_LLM_RESPONSE_ERROR_MESSAGE}\n{e}")
            # エラーメッセージの画面表示
            st.error(utils.build_error_message(ct.GET_LLM_RESPONSE_ERROR_MESSAGE), icon=ct.ERROR_ICON)
            # 後続の処理を中断
            st.stop()
    
    # ==========================================
    # 7-3. LLMからの回答表示
    # ==========================================
    with st.chat_message("assistant"):
        try:
            # ==========================================
            # モードが「社内文書検索」の場合
            # ==========================================
            if st.session_state.mode == ct.ANSWER_MODE_1:
                # 入力内容と関連性が高い社内文書のありかを表示
                content = cn.display_search_llm_response(llm_response)

            # ==========================================
            # モードが「社内問い合わせ」の場合
            # ==========================================
            elif st.session_state.mode == ct.ANSWER_MODE_2:
                # 入力に対しての回答と、参照した文書のありかを表示
                content = cn.display_contact_llm_response(llm_response)
            
            # AIメッセージのログ出力
            logger.info({"message": content, "application_mode": st.session_state.mode})
        except Exception as e:
            # エラーログの出力
            logger.error(f"{ct.DISP_ANSWER_ERROR_MESSAGE}\n{e}")
            # エラーメッセージの画面表示
            st.error(utils.build_error_message(ct.DISP_ANSWER_ERROR_MESSAGE), icon=ct.ERROR_ICON)
            # 後続の処理を中断
            st.stop()

    # ==========================================
    # 7-4. 会話ログへの追加
    # ==========================================
    # 表示用の会話ログにユーザーメッセージを追加
    st.session_state.messages.append({"role": "user", "content": chat_message})
    # 表示用の会話ログにAIメッセージを追加
    st.session_state.messages.append({"role": "assistant", "content": content})

    # ==========================================
    # 7-5. 人事部に所属している従業員情報の検索と表示
    # ==========================================
    if "人事部に所属している従業員情報を一覧化して" in chat_message:
        try:
            # CSVファイルの読み込み
            employee_data = pd.read_csv(os.path.join(ct.RAG_TOP_FOLDER_PATH, "社員名簿.csv"))
            # 人事部に所属している従業員情報をフィルタリング
            hr_employees = employee_data[employee_data["部署"] == "人事部"]
            # 結果を表示
            if not hr_employees.empty:
                st.write("人事部に所属している従業員情報:")
                st.write(hr_employees)
            else:
                st.write("人事部に所属している従業員情報が見つかりませんでした。")
        except Exception as e:
            st.error(f"従業員情報の取得に失敗しました: {e}")

# ドキュメントデータのロード
try:
    docs = []
    for ext, loader in ct.SUPPORTED_EXTENSIONS.items():
        for file in os.listdir(ct.RAG_TOP_FOLDER_PATH):
            if file.endswith(ext):
                docs.extend(loader(os.path.join(ct.RAG_TOP_FOLDER_PATH, file)).load())
except Exception as e:
    st.error(f"Error loading documents: {e}")
    st.stop()

# ベクターストアの設定
embeddings = OpenAIEmbeddings()
db = Chroma.from_documents(docs, embedding=embeddings)

# 検索スコアの閾値を設定
retriever = db.as_retriever(search_kwargs={"k": 5, "score_threshold": 0.8})

# 社内問い合わせの処理
if st.session_state.mode == ct.ANSWER_MODE_2:
    with st.spinner(ct.SPINNER_TEXT):
        try:
            # ユーザーの入力に基づいてベクターストアから関連するドキュメントを検索
            results = retriever.retrieve(chat_message)
            if results:
                # 検索結果を表示
                st.write("関連するドキュメント:")
                for result in results:
                    st.write(result["content"])
            else:
                st.write("該当資料なし")
        except Exception as e:
            st.error(f"ドキュメントの検索に失敗しました: {e}")