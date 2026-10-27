"""Read the ready-made dataset in dataset/ (characters.csv and questions.csv)."""
import csv


class Dataset:
    VALUES = {"true": True, "false": False, "unknown": None}
    ATTRIBUTES_Char = {"name", "sitelinks", "source"}

    @staticmethod
    def parse_value(text):
        """Turn "true" / "false" / "unknown" into True / False / None."""
        if text in Dataset.VALUES:
            return Dataset.VALUES[text]
        else:
            raise ValueError("unknown value: " + text)

    @staticmethod
    def load_characters(path):
        """Read the ready-made dataset in csv format."""
        characters = []
        with open(path, mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            # Iterate over the rows
            for row in csv_reader:
                character = {}
                attributes = {}
                for key, value in row.items():
                    if key not in Dataset.ATTRIBUTES_Char:
                        attributes[key] = Dataset.parse_value(value)
                    if key == "name":
                        character[key] = value
                    if key == "sitelinks":
                        character[key] = int(value)
                character["attributes"] = attributes
                characters.append(character)
        return characters

    @staticmethod
    def load_questions(path):
        """Read the ready-made dataset in csv format."""
        questions = {}
        with open(path, mode='r', newline="", encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                questions[row["attribute"]] = row["question"]
        return questions

    @staticmethod
    def load_parents(path):
        """Read narrower question -> broader parent question from questions.csv (rows without a parent are skipped)."""
        parents = {}
        with open(path, mode='r', newline="", encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                if row.get("parent"):
                    parents[row["attribute"]] = row["parent"]
        return parents
