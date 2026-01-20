import gspread
import json
import sys
import argparse
from typing import Optional, Any


class Sheet:
    """
    Manages Google Sheets data for tracking people's availability and records of their snow removals.
    This is used for managing snow removal scheduling.

    This class provides methods to read Google Sheets data, validate respondents
    exist in the dataset, and retrieve availability information for specific days.

    Private Attributes:
        __api_key: Path to the Google Sheets API key
        __sheet_name: Name of the Google Sheet
        __worksheet_name: Name of the worksheet to access within the spreadsheet
        __sheet: List of dictionaries containing the worksheet records

    Public Methods:
        update(): updates the internal sheet
        duplicates(): Finds duplicate Name entries
        missing(other): Validates the respondent exist in the sheet's records
        availability(other, day): Gets people available on a specific day with removal counts

    Properties:
        sheet: Returns the raw worksheet data as a list of dictionaries
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        sheet_name: Optional[str] = None,
        worksheet_name: Optional[str] = None,
        data: Optional[list[dict[str, Any]]] = None,
    ):
        self.__api_key: Optional[str] = api_key
        self.__sheet_name: Optional[str] = sheet_name
        self.__worksheet_name: Optional[str] = worksheet_name

        if data is not None:
            self.__sheet = data
        else:
            self.__sheet = []

    def update(self) -> list[dict[str, Any]]:
        """
        Gets the Google Sheet data from the Google Sheet API and updates the internal sheet.

        Returns:
            List of dictionaries where each dictionary represents a row with
            column headers as keys. Returns empty list if an error occurs.
            For "Responses" worksheet, the "Days" field is converted to a list
            and the "Replacement" field is removed (it is just a check that acknowledges
            they will find a replacement if they cannot make a day they signed up for).

        Raises:
            ValueError: If `__api_key`, `__sheet_name`, or `__worksheet_name` is None.
            FileNotFoundError: If the API key file does not exist.
            ValueError: If the specified spreadsheet does not exist.
            ValueError: If the specified worksheet does not exist.
        """

        if not self.__api_key or not self.__sheet_name or not self.__worksheet_name:
            raise ValueError(
                "API key, sheet name, and worksheet name must all be provided"
            )

        try:
            # Needed logic to get data from the Google Sheet API
            client: gspread.Client = gspread.service_account(filename=self.__api_key)
            spreadsheet: gspread.Spreadsheet = client.open(self.__sheet_name)
            worksheet: gspread.Worksheet = spreadsheet.worksheet(self.__worksheet_name)
            sheet: list[dict[str, Any]] = worksheet.get_all_records()

            if sheet != []:
                for row in sheet:
                    # Helps to normalize data by removing trailing whitespace
                    row["Name"] = row["Name"].strip()
                    if self.__worksheet_name == "Responses":
                        # Turns the "Days" response into a list for easier processing
                        row["Days"] = [day.strip() for day in row["Days"].split(",")]

                        # The replacement row is just a checkbox that acknowledges they must
                        # find a replacement if they cannot make a day they sign up for
                        del row["Replacement"]

            self.__sheet = sheet
            return self.__sheet

        # Returns more readable errors
        except FileNotFoundError:
            raise FileNotFoundError(f"API key file '{self.__api_key}' not found")
        except gspread.exceptions.SpreadsheetNotFound:
            raise ValueError(f"Spreadsheet '{self.__sheet_name}' not found")
        except gspread.exceptions.WorksheetNotFound:
            raise ValueError(f"Worksheet '{self.__worksheet_name}' not found")

    def duplicates(self) -> set[str]:
        """
        Finds duplicated responses

        Returns:
            Set of names that exist multiple times in responses.
        """

        people: set[str] = set()
        duplicated: set[str] = set()

        # Records people to find duplicates, and adds them to set
        for entry in self.__sheet:
            person = entry["Name"]
            if person.lower() in people:
                duplicated.add(person)
            else:
                people.add(person.lower())

        return duplicated

    def missing(self, other: "Sheet") -> set[str]:
        """
        Compares this sheet's respondents against another sheet's records.

        Args:
            other: Sheet object containing user records to validate against

        Returns:
            Set of names that exist in responses but not in the records.
        """

        missing: set[str] = set()
        lookup: set[str] = set(entry["Name"].lower() for entry in other.__sheet)

        # Adds people missing from records to set
        for response in self.__sheet:
            respondent: str = response["Name"]
            if respondent.lower() not in lookup:
                missing.add(respondent)

        return missing

    def availability(
        self, other: "Sheet", day: str
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """
        Lists the available people to work on a given day,
        with the amount of snow removals theyve already done.

        Args:
            other: Sheet object containing user records to check against
            day: The day of the week to check

        Returns:
            A Tuple containing the following:
                The sorted list of dictionaries of everyone who can make the day, including:
                    the number of removals they've done
                    their leadership status
                    their varsity status
                The optimal list for who can make the day
        """

        if day not in (
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ):
            raise ValueError(f"Invalid day: {day}. Must be a day of the week.")

        # Store results and builds a lookup dictionary for peoples records
        results: list[dict[str, Any]] = []
        lookup: dict[str, dict[str, Any]] = {
            entry["Name"].lower(): {
                "Completed": entry["Completed"],
                "Experience": entry["Experience"],
                "Position": entry["Position"],
            }
            for entry in other.__sheet
        }

        # Adds all the people and their records who are available on the day to the results
        for response in self.__sheet:
            if day in response["Days"]:
                if record := lookup.get(response["Name"].lower()):
                    results.append(
                        {
                            "Name": response["Name"],
                            "Completed": record["Completed"],
                            "Experience": record["Experience"],
                            "Position": record["Position"],
                        }
                    )

        # Sorts the list by snow removals done
        results.sort(key=lambda x: x["Completed"])

        team: list[str] = []
        novices: int = 0

        # Gets the team leader for the group
        for result in results:
            if result["Position"] == "Leader":
                team.append(result["Name"])
                break

        if not team:
            raise ValueError(f"No leader available for {day}")

        # Builds the rest of the team list
        for result in results:
            if len(team) == 6:
                break
            elif result["Position"] == "Leader":
                continue
            elif result["Experience"] == "Varsity":
                team.append(result["Name"])
            elif novices < 3:
                team.append(result["Name"])
                novices += 1

        return results, team

    @property
    def sheet(self) -> list[dict[str, Any]]:
        """
        Returns the raw worksheet data.

        Returns:
            List of dictionaries where each dictionary represents a row
            with column headers as keys
        """

        return self.__sheet


def read_config() -> dict[str, Any]:
    """
    Reads and parses the configuration file.

    Returns:
        Dictionary containing API key path, sheet name, and worksheet names

    Raises:
        FileNotFoundError: If config.json is not found
        json.JSONDecodeError: If config.json is invalid JSON
    """

    with open("config.json", "r") as config:
        return json.load(config)


if __name__ == "__main__":
    # Setup the parser
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--day", help="Day to list (e.g. Monday)")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show debug output"
    )
    args = parser.parse_args()

    # Read config
    try:
        config: dict = read_config()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading configuration: {e}")
        sys.exit(1)

    # Creates the sheets based on the config file
    try:
        responses = Sheet(
            config["api_key_path"],
            config["sheet_name"],
            config["worksheets"]["responses"],
        )
        responses.update()

        records = Sheet(
            config["api_key_path"],
            config["sheet_name"],
            config["worksheets"]["records"],
        )
        records.update()

    except (ValueError, FileNotFoundError) as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)

    error: bool = False

    # Prints the missing people
    if missing := responses.missing(records):
        print("Users Who Do Not Exist In The Records:\n")
        for person in missing:
            print(person)
        print()
        error = True

    # Prints any duplicates
    if duplicated := responses.duplicates():
        print("Duplicates Found:\n")
        for duplicate in duplicated:
            print(duplicate)
        print()
        error = True

    if error:
        sys.exit(1)

    # Determine day
    if args.day:
        day: str = args.day.strip().title()
    else:
        day: str = input("Day To List: ").strip().title()

    # Get the groups for a day
    debug: list[dict[str, Any]]
    team: list[str]
    debug, team = responses.availability(records, day)

    # Print the full dictionary
    if args.verbose:
        print("DEBUG DATA:")
        for entry in debug:
            print(entry)
        print()

    # Print just the team
    for member in team:
        print(member)
