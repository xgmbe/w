import re
import time
import csv
import pandas as pd
import urllib.parse
from io import StringIO
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


# Function to initialize the WebDriver
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument(
        "--disable-dev-shm-usage"
    )  # Overcome limited resource problems
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://web.whatsapp.com/")
    return driver


# Function to check QR scan
def check_qr_scan(driver):
    try:
        wait = WebDriverWait(driver, 120)  # Adjust this time as needed
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//canvas[@aria-label='Scan me!']")
            )
        )
        st.success("Please scan the QR code. Waiting...")
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='side']")))
        st.success("QR code scanned successfully. Proceeding...")
        return True
    except TimeoutException:
        st.error("QR code scan failed. Please try again.")
        return False


# Send Messages Function
# Global set to track successful message sends
if "successful_numbers" not in st.session_state:
    st.session_state.successful_numbers = set()


def send_messages(driver, numbers, message, sleep_time):
    encoded_message = urllib.parse.quote(message)
    for number in numbers:
        try:
            link = (
                f"https://web.whatsapp.com/send?phone={number}&text={encoded_message}"
            )
            driver.get(link)
            # Use WebDriverWait to wait for the send button to be clickable
            WebDriverWait(driver, 45).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Enviar']"))
            )
            send_button = driver.find_element(
                By.XPATH, "//button[@aria-label='Enviar']"
            )
            send_button.click()  # Click the send button
            st.session_state.successful_numbers.add(number)

            time.sleep(sleep_time)
        except Exception as e:
            print(f"Failed to send message to {number}. Error: {e}")


# Function to scrape contacts
def scrape_contacts(driver):
    if "unique_numbers" not in st.session_state:
        st.session_state.unique_numbers = set()

    contacts_section_xpath = "/html/body/div[1]/div/span[2]/div/span/div/div/div/div/div/div/div[2]/div/div/div"  # Adjust this XPATH as needed
    pattern = re.compile(r"\+\d{1,3}\s\d+")

    contacts_section = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, contacts_section_xpath))
    )
    phone_number_elements = contacts_section.find_elements(
        By.XPATH, ".//span[contains(@class, '_11JPr')]"
    )

    for element in phone_number_elements:
        text = element.text
        if pattern.match(text):
            st.session_state.unique_numbers.add(text)


# Function to convert unique numbers to CSV
def unique_numbers_to_csv(unique_numbers):
    csv_in_memory = StringIO()
    writer = csv.writer(csv_in_memory)
    writer.writerow(["Phone Number"])
    for number in unique_numbers:
        writer.writerow([number])
    csv_in_memory.seek(0)
    return csv_in_memory.getvalue()


def successful_numbers_to_csv(successful_numbers):
    csv_in_memory = StringIO()
    writer = csv.writer(csv_in_memory)
    writer.writerow(["Phone Number"])
    for number in successful_numbers:
        writer.writerow([number])
    csv_in_memory.seek(0)
    return csv_in_memory.getvalue()


# Streamlit UI setup
st.title("WhatsApp Automation")
# Scrape Contacts Section
st.subheader("Scrape Contacts")

if "driver" not in st.session_state:
    if st.button("Initialize WhatsApp Web"):
        st.session_state.driver = init_driver()
        if check_qr_scan(st.session_state.driver):
            st.session_state.qr_scanned = True

if st.session_state.get("qr_scanned", False):
    st.warning(
        f"Current number of unique contacts scraped: {len(st.session_state.get('unique_numbers', []))}"
    )
    if st.button("Scrape Contacts Again"):
        scrape_contacts(st.session_state.driver)
        st.success("Scraped again. Check for new numbers.")

    if st.session_state.get("unique_numbers"):
        csv_data = unique_numbers_to_csv(st.session_state.unique_numbers)
        st.download_button(
            "Download Phone Numbers CSV",
            data=csv_data,
            # csv file name
            file_name="phone_numbers.csv",
            mime="text/csv",
        )
    # Send Messages Section
    st.subheader("Send Messages")
    uploaded_file = st.file_uploader("Upload CSV with phone numbers", type="csv")
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        numbers = df["Phone Number"].tolist()
        message = st.text_area(
            "Message:", "Hello, this is a test message from Streamlit!"
        )
        sleep_time = st.number_input(
            "Seconds to wait between messages:", min_value=1, value=10
        )
        if st.button("Send Messages"):
            # spiner
            with st.spinner("Sending messages..."):
                send_messages(st.session_state.driver, numbers, message, sleep_time)
                st.success("Messages sent successfully.")

            if st.session_state.get("successful_numbers"):
                csv_data_success = successful_numbers_to_csv(
                    st.session_state.successful_numbers
                )
                st.download_button(
                    label="Download Successful Messages Phone Numbers CSV",
                    data=csv_data_success,
                    file_name="successful_phone_numbers.csv",
                    mime="text/csv",
                )
