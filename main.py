import datetime
import os
import speech_recognition as sr
import pyttsx3
import webbrowser as wb
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import openai
from dotenv import load_dotenv
import openai.error
import tkinter as tk
from tkinter import messagebox, simpledialog

# Load environment variables from the .env file
load_dotenv()

# Access the OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Define rate limits
RATE_LIMITS = {
    "tokens_per_minute": 40000,
    "requests_per_minute": 3,
    "requests_per_day": 200
}

# Initialize counters
token_counter = 0
request_counter = 0
start_time = time.time()
day_start_time = time.time()

websites = {
    "YouTube": "https://youtube.com",
    "Google": "https://google.com",
    "Facebook": "https://facebook.com",
    "Twitter": "https://twitter.com",
    "Instagram": "https://instagram.com",
    "Reddit": "https://reddit.com",
    "WhatsApp": "https://web.whatsapp.com/"
}

music_websites = {
    "SoundCloud": "https://soundcloud.com/search?q=",
    "YouTube Music": "https://music.youtube.com/search?q="
}

code_editors = {
    "vscode": r"C:\Users\BASIT\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Visual Studio Code",
    "intellij idea": r"C:\Program Files\JetBrains\IntelliJ IDEA Community Edition 2024.1\bin\idea64.exe",
    "pycharm": r"C:\Program Files\JetBrains\PyCharm Community Edition 2024.1\bin\pycharm64.exe",
    "net beans": r"C:\Program Files\NetBeans 12.6\bin\netbeans64.exe"
}

def check_rate_limits():
    global token_counter, request_counter, start_time, day_start_time

    current_time = time.time()
    elapsed_time = current_time - start_time
    day_elapsed_time = current_time - day_start_time

    # Reset counters if a minute has passed
    if elapsed_time > 60:
        token_counter = 0
        request_counter = 0
        start_time = current_time

    # Reset daily request counter if a day has passed
    if day_elapsed_time > 86400:  # 24 hours * 60 minutes * 60 seconds
        request_counter = 0
        day_start_time = current_time

    # Check request limits
    if request_counter >= RATE_LIMITS["requests_per_minute"]:
        time_to_wait = 60 - elapsed_time
        print(f"Rate limit reached. Waiting for {time_to_wait:.2f} seconds.")
        time.sleep(time_to_wait)
        token_counter = 0
        request_counter = 0
        start_time = time.time()

    if request_counter >= RATE_LIMITS["requests_per_day"]:
        print("Daily rate limit reached. Please try again tomorrow.")
        return False

    return True


def say(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def take_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = r.listen(source)
    try:
        print("Recognizing...")
        query = r.recognize_google(audio, language="en-in")
        print(f"User said: {query}")
    except sr.UnknownValueError:
        print("Sorry, I did not get that")
        return "None"
    except sr.RequestError:
        print("Sorry, the service is down")
        return "None"
    return query


def open_website(query):
    for keyword, url in websites.items():
        if keyword.lower() in query.lower():
            wb.open(url)
            say(f"Opening {keyword}")
            break
    else:
        say("No matching websites found")


def play_music(query):
    song_title = query.replace("play", "", 1).strip()
    if not song_title:
        say("Please specify a song to play")
        return

    # Set up the webdriver with webdriver_manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    wait = WebDriverWait(driver, 10)

    for platform, search_url in music_websites.items():
        search_query = search_url + song_title.replace(" ", "+")
        driver.get(search_query)

        try:
            if platform == "SoundCloud":
                reject_all = wait.until(
                    EC.presence_of_element_located((By.ID, "onetrust-reject-all-handler"))
                )
                if reject_all:
                    reject_all.click()
                play_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH,
                                                '/html/body/div[1]/div[2]/div[2]/div/div/div[3]/div/div/div/ul/li[1]/div/div/div/div[2]/div[1]/div/div/div[1]/a'))
                )
            elif platform == "YouTube Music":
                play_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'ytmusic-play-button-renderer'))
                )

            # Scroll into view and click the play button
            driver.execute_script("arguments[0].scrollIntoView(true);", play_button)
            time.sleep(1)  # Wait a bit for scrolling to complete
            driver.execute_script("arguments[0].click();", play_button)
            say(f"Playing {song_title} on {platform}")

            # Exit the loop after successfully starting the song
            break

        except Exception as e:
            print(f"Could not play on {platform}: {e}")

    return driver


def get_date_info(query):
    today = datetime.date.today()
    if "today" in query.lower():
        target_date = today
    elif "tomorrow" in query.lower():
        target_date = today + datetime.timedelta(days=1)
    else:
        try:
            day_offset = int(query.split()[-1])
            target_date = today + datetime.timedelta(days=day_offset)
        except (ValueError, IndexError):
            say("I didn't understand the date you mentioned.")
            return

    day_of_week = target_date.strftime("%A")
    say(f"The date is {target_date} and the day is {day_of_week}")


def open_drive(query):
    drive_letter = query.split()[-1].upper()
    if len(drive_letter) == 1 and drive_letter.isalpha():
        os.system(f'explorer {drive_letter}:\\')
        say(f"Opening drive {drive_letter}")
        list_drive_contents(drive_letter)
    else:
        say("I didn't understand the drive you mentioned.")


def list_drive_contents(drive_letter):
    path = f'{drive_letter}:\\'
    try:
        contents = os.listdir(path)
        if contents:
            say("The drive contains the following files and folders:")
            for item in contents:
                say(item)
            ask_to_open_item(path, contents)
        else:
            say("The drive is empty.")
    except Exception as e:
        say(f"Could not list contents of drive {drive_letter}: {e}")


def ask_to_open_item(path, contents):
    while True:
        say("Would you like to open any specific file or folder?")
        query = take_command()

        if query != "None":
            if "no" in query.lower():
                say("Enjoy the opened folder")
                return
            else:
                for item in contents:
                    if item.lower() in query.lower():
                        item_path = os.path.join(path, item)
                        os.startfile(item_path)
                        if os.path.isfile(item_path):
                            say(f"Opening {item}. Enjoy it!")
                        else:
                            say(f"Opening {item}")
                        break
                else:
                    say("No matching file or folder found.")
        else:
            say("Sorry, I didn't understand. Can you go again, please?")
            query = take_command()
            if query == "None":
                continue
            else:
                for item in contents:
                    if item.lower() in query.lower():
                        item_path = os.path.join(path, item)
                        os.startfile(item_path)
                        if os.path.isfile(item_path):
                            say(f"Opening {item}. Enjoy it!")
                        else:
                            say(f"Opening {item}")
                        break
                else:
                    say("No matching file or folder found.")


def open_code_editor(query):
    for keyword, path in code_editors.items():
        if keyword.lower() in query.lower():
            if os.path.exists(path):
                os.startfile(path)
                say(f"Opening {keyword}")
                break
            else:
                say(f"Path for {keyword} not found or is incorrect")
                break
    else:
        say("No matching code editor found or path is incorrect")


def chat_with_openai(query):
    global token_counter, request_counter

    if not check_rate_limits():
        return "Rate limit reached. Please try again later."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": query}
            ],
            temperature=1,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        # Update counters
        token_counter += response['usage']['total_tokens']
        request_counter += 1

        answer = response.choices[0].message['content']
        say(answer)
        return answer
    except openai.error.RateLimitError:
        error_message = "You have exceeded your current quota. Please check your plan and billing details."
        say(error_message)
        return error_message
    except openai.error.OpenAIError as e:
        error_message = f"An error occurred: {e}"
        say(error_message)
        return error_message


def handle_query(query):
    if "what's your name" in query.lower():
        say("My name is Jarvis")
    elif "open" in query.lower() and "website" in query.lower():
        open_website(query)
    elif "play" in query.lower() and "music" in query.lower():
        driver = play_music(query)
    elif "date" in query.lower() or "day" in query.lower():
        get_date_info(query)
    elif "open" in query.lower() and "drive" in query.lower():
        open_drive(query)
    elif "open" in query.lower() and ("editor" in query.lower() or "code" in query.lower()):
        open_code_editor(query)
    else:
        chat_response = chat_with_openai(query)
        print(chat_response)
        return chat_response


class JarvisGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Jarvis A.I")
        self.root.geometry("500x400")

        self.label = tk.Label(root, text="Welcome to Jarvis A.I", font=("Arial", 20))
        self.label.pack(pady=10)

        self.query_entry = tk.Entry(root, width=30, font=("Arial", 14))
        self.query_entry.pack(pady=20)

        self.submit_button = tk.Button(root, text="Submit", command=self.submit_query, font=("Arial", 14))
        self.submit_button.pack(pady=10)

        self.listen_button = tk.Button(root, text="Listen", command=self.listen_query, font=("Arial", 14))
        self.listen_button.pack(pady=10)

        self.response_text = tk.Text(root, width=60, height=10, font=("Arial", 14))
        self.response_text.pack(pady=20)

    def submit_query(self):
        query = self.query_entry.get()
        if query:
            response = handle_query(query)
            self.response_text.insert(tk.END, f"You: {query}\n")
            self.response_text.insert(tk.END, f"Jarvis: {response}\n")
            self.query_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Warning", "Please enter a query")

    def listen_query(self):
        query = take_command()
        if query != "None":
            self.query_entry.delete(0, tk.END)
            self.query_entry.insert(0, query)
            self.submit_query()
        else:
            messagebox.showwarning("Warning", "Sorry, I did not get that")


if __name__ == "__main__":
    root = tk.Tk()
    gui = JarvisGUI(root)
    root.mainloop()
