from enum import StrEnum
from random import choice, randint, random
from typing import List, Optional
import csv
from datetime import datetime
import os

from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
import time

GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSe42EEaKgfigJukDIwsccpfAdQ4uqQvLIshQAcW5hDFCid0Ew/viewform"
CSV_FILENAME = "form_responses.csv"

# Prioritized choices
PRIORITIZED_CHOICES = {
    "Female",
    "18-24",
    "Other country",
    "Several times a month",
    "Agree",
    "Likely",
    "Mainly foreign brands",
    "Neutral",
    "4",
    "3",
}
PRIORITY_PROBABILITY = 0.6


class CssSelector(StrEnum):
    FIELDS = ".geS5n"
    OPTION = ".nWQGrd.zwllIb"
    MULTI_OPTION = ".eBFwI"
    QUESTION_TITLE = ".M7eMe"
    SEND_BUTTON = ".l4V7wb.Fxmcue"


def initialize_driver() -> webdriver.Chrome:
    """Initialize and return a Chrome WebDriver instance."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")

    print("Starting driver using Chrome...")
    return webdriver.Chrome(options=chrome_options)


def find_elements(driver: webdriver.Chrome, css_selector: str) -> List[WebElement]:
    """Find and return elements by CSS selector."""
    return driver.find_elements(By.CSS_SELECTOR, css_selector)


def get_question_text(field: WebElement) -> str:
    """Extract the question text from a field."""
    try:
        question_element = field.find_element(By.CSS_SELECTOR, CssSelector.QUESTION_TITLE)
        return question_element.text.strip()
    except NoSuchElementException:
        return "Unknown Question"


def find_prioritized_option(options: List[WebElement]) -> Optional[WebElement]:
    """Find a prioritized option from the list if available."""
    for option in options:
        option_text = option.text.strip()
        # Check if option text matches or contains any prioritized choice
        for prioritized in PRIORITIZED_CHOICES:
            if prioritized.lower() in option_text.lower() or option_text.lower() in prioritized.lower():
                return option
    return None


def select_option(field: WebElement) -> tuple[str, str]:
    """Select an option from a single-choice field, prioritizing specific choices."""
    question = get_question_text(field)
    options = field.find_elements(By.CSS_SELECTOR, CssSelector.OPTION)

    try:
        selected_option = None

        # Try to find and use prioritized option with 80% probability
        if random() < PRIORITY_PROBABILITY:
            prioritized_option = find_prioritized_option(options)
            if prioritized_option:
                selected_option = prioritized_option
                print(f"  [PRIORITIZED] ", end="")

        # If no prioritized option was selected, choose random
        if selected_option is None:
            selected_option = choice(options)

        selected_option.click()
        answer = selected_option.text
        print(f"Selected option: {answer}")
        return question, answer
    except IndexError:
        return select_multi_option(field)


def select_multi_option(field: WebElement) -> tuple[str, str]:
    """Select options from a multi-choice field, prioritizing specific choices."""
    question = get_question_text(field)
    multi_options = field.find_elements(By.CSS_SELECTOR, CssSelector.MULTI_OPTION)
    buffer = []

    # First, try to select prioritized options
    prioritized_selected = False
    for multi_option in multi_options:
        option_text = multi_option.text.strip()
        for prioritized in PRIORITIZED_CHOICES:
            if (prioritized.lower() in option_text.lower() or
                    option_text.lower() in prioritized.lower()):
                if random() < PRIORITY_PROBABILITY and option_text not in buffer:
                    multi_option.click()
                    print(f"  [PRIORITIZED] Selected option: {option_text}")
                    buffer.append(option_text)
                    prioritized_selected = True
                    break

    # If no prioritized options were selected or we want more selections
    if not prioritized_selected or (len(buffer) < len(multi_options) and random() < 0.3):
        remaining_count = randint(1, max(1, len(multi_options) - len(buffer)))
        for i in range(remaining_count):
            multi_option = multi_options[randint(0, len(multi_options) - 1)]
            if multi_option.text not in buffer:
                multi_option.click()
                print(f"Selected option: {multi_option.text}")
                buffer.append(multi_option.text)

    answer = "; ".join(buffer)
    return question, answer


def save_to_csv(form_data: dict) -> None:
    """Save form data to CSV file."""
    file_exists = os.path.isfile(CSV_FILENAME)

    with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as csvfile:
        # Create headers from form data keys
        fieldnames = ['Timestamp'] + list(form_data.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header only if file doesn't exist
        if not file_exists:
            writer.writeheader()

        # Add timestamp and write row
        row_data = {'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        row_data.update(form_data)
        writer.writerow(row_data)

    print(f"\nData saved to {CSV_FILENAME}")


def fill_form(driver: webdriver.Chrome) -> dict:
    """Fill all fields in the Google Form and return collected data."""
    time.sleep(1)

    form_data = {}
    all_fields = find_elements(driver, CssSelector.FIELDS)

    for i, field in enumerate(all_fields):
        print(f"\nQuestion {i + 1}:")
        question, answer = select_option(field)
        form_data[question] = answer

    return form_data

def apply_form(driver: webdriver.Chrome) -> None:
    """Apply form data to Google Form."""
    driver.find_element(By.CSS_SELECTOR, CssSelector.SEND_BUTTON).click()

def main() -> None:
    """Main function to automate Google Form filling."""
    driver = initialize_driver()
    count = int(input("How many forms to fill? "))

    for i in range(count):
        try:
            print(f"Opening Google Form URL: {GOOGLE_FORM_URL}")
            driver.get(GOOGLE_FORM_URL)

            form_data = fill_form(driver)
            apply_form(driver)
            save_to_csv(form_data)

            print("\n--- Form Data Summary ---")
            for question, answer in form_data.items():
                print(f"{question}: {answer}")

            time.sleep(2)
        except KeyboardInterrupt:
            print("Keyboard interrupt\nStopping.")
            break

    driver.quit()


if __name__ == "__main__":
    main()