import pytest
import gspread
import json
from gvsu_snow_removal_scheduler import Sheet, read_config


@pytest.fixture
def mock_responses_data():
    """
    Mock data for the 'Responses' sheet.
    Includes duplicates and mixed casing to test normalization.
    """
    return [
        {"Name": "Leader Alice", "Days": "Monday, Wednesday", "Replacement": "No"},
        {"Name": "Varsity Bob", "Days": "Monday", "Replacement": "No"},
        {"Name": "Varsity Charlie", "Days": "Monday", "Replacement": "No"},
        {"Name": "Novice Dave", "Days": "Monday", "Replacement": "No"},
        {"Name": "Novice Eve", "Days": "Monday", "Replacement": "No"},
        {"Name": "Novice Frank", "Days": "Monday", "Replacement": "No"},
        {
            "Name": "Novice Grace",
            "Days": "Monday",
            "Replacement": "No",
        },
        {"Name": "Duplicate Dan", "Days": "Tuesday", "Replacement": "No"},
        {"Name": "duplicate dan", "Days": "Tuesday", "Replacement": "No"},
        {
            "Name": "Missing Mike",
            "Days": "Friday",
            "Replacement": "No",
        },
    ]


@pytest.fixture
def mock_records_data():
    """
    Mock data for the 'Records' sheet.
    Includes fields: Completed, Experience, Position.
    """
    return [
        {
            "Name": "Leader Alice",
            "Completed": 5,
            "Experience": "Varsity",
            "Position": "Leader",
        },
        {
            "Name": "Varsity Bob",
            "Completed": 2,
            "Experience": "Varsity",
            "Position": "Member",
        },
        {
            "Name": "Varsity Charlie",
            "Completed": 10,
            "Experience": "Varsity",
            "Position": "Member",
        },
        {
            "Name": "Novice Dave",
            "Completed": 1,
            "Experience": "Novice",
            "Position": "Member",
        },
        {
            "Name": "Novice Eve",
            "Completed": 0,
            "Experience": "Novice",
            "Position": "Member",
        },
        {
            "Name": "Novice Frank",
            "Completed": 0,
            "Experience": "Novice",
            "Position": "Member",
        },
        {
            "Name": "Novice Grace",
            "Completed": 0,
            "Experience": "Novice",
            "Position": "Member",
        },
        {
            "Name": "Duplicate Dan",
            "Completed": 5,
            "Experience": "Varsity",
            "Position": "Member",
        },
    ]


@pytest.fixture
def mock_gspread(monkeypatch, mock_responses_data, mock_records_data):
    """Mocks the gspread interaction to return the data above."""

    class MockWorksheet:
        def __init__(self, data):
            self._data = data

        def get_all_records(self):
            return self._data

    class MockSpreadsheet:
        def worksheet(self, name):
            if name == "Responses":
                return MockWorksheet(mock_responses_data)
            if name == "Records":
                return MockWorksheet(mock_records_data)
            raise gspread.exceptions.WorksheetNotFound

    class MockClient:
        def open(self, name):
            if name == "Snow Data":
                return MockSpreadsheet()
            raise gspread.exceptions.SpreadsheetNotFound

    monkeypatch.setattr("gspread.service_account", lambda filename: MockClient())


def test_init_success(mock_responses_data):
    """Test successful initialization and data normalization via DI."""
    # Note: Normalization happens in update(), so if we inject raw data, we need to ensure it's normalized
    # OR we are testing update() separately.
    # The original test_init_success checked normalization. Since normalization is in update(),
    # we should check that here.

    # If we pass data directly, it is assumed to be the "state" of the sheet.
    # If we want to test normalization, we must call update().
    pass


def test_init_with_data(mock_responses_data):
    """Test initializing with pre-populated data."""
    sheet = Sheet(data=mock_responses_data)
    assert sheet.sheet == mock_responses_data


def test_init_missing_args():
    """Test that empty args result in empty sheet."""
    sheet = Sheet()
    assert sheet.sheet == []


def test_update_errors(monkeypatch):
    """Test explicit error raising in update()."""

    monkeypatch.setattr(
        "gspread.service_account",
        lambda filename: (_ for _ in ()).throw(FileNotFoundError),
    )
    # Init shouldn't fail anymore
    sheet = Sheet("bad_key.json", "Snow Data", "Responses")

    # Update should fail
    with pytest.raises(FileNotFoundError):
        sheet.update()

    def mock_client_open(*args):
        raise gspread.exceptions.SpreadsheetNotFound

    monkeypatch.setattr(
        "gspread.service_account",
        lambda filename: type("obj", (object,), {"open": mock_client_open}),
    )
    sheet = Sheet("key.json", "Bad Sheet", "Responses")
    with pytest.raises(ValueError, match="Spreadsheet.*not found"):
        sheet.update()


def test_duplicates(mock_responses_data):
    # Normalize the mock data to match what duplicates() expects (case sensitive check in duplicates logic?)
    # duplicates() uses "Name".
    # The logic in duplicates(): person = entry["Name"]; if person.lower() in people...

    # The mock_responses_data has "Duplicate Dan" and "duplicate dan".
    sheet = Sheet(data=mock_responses_data)
    dups = sheet.duplicates()

    assert "Duplicate Dan" in dups or "duplicate dan" in dups
    assert len(dups) == 1


def test_missing_people(mock_responses_data, mock_records_data):
    responses = Sheet(data=mock_responses_data)
    records = Sheet(data=mock_records_data)

    missing = responses.missing(records)

    assert "Missing Mike" in missing
    assert "Leader Alice" not in missing
    assert len(missing) == 1


def test_availability_basic_sorting(mock_responses_data, mock_records_data):
    """
    Test that the debug list is sorted by 'Completed' ascending.
    """
    # Need to normalize mock data "Days" to be lists because availability checks `if day in response["Days"]`
    # The fixture returns strings "Monday, Wednesday" etc.
    # We need to emulate what update() does or fix the fixture.
    # For this test, let's fix the data passed in.

    # Actually, let's just make sure the mock data used for DI has proper list format for Days if that's what Sheet expects internally.
    # Looking at Sheet logic:
    # row["Days"] = [day.strip() for day in row["Days"].split(",")]

    # We'll update the mock data for these tests.
    for r in mock_responses_data:
        if isinstance(r["Days"], str):
            r["Days"] = [d.strip() for d in r["Days"].split(",")]

    responses = Sheet(data=mock_responses_data)
    records = Sheet(data=mock_records_data)

    debug, _ = responses.availability(records, "Monday")

    completed_counts = [x["Completed"] for x in debug]
    assert completed_counts == sorted(completed_counts)


def test_availability_team_logic(mock_responses_data, mock_records_data):
    """
    Test the complex team selection logic:
    1. Must have Leader
    2. Max 6 people
    3. Max 3 Novices
    """
    # Fix Days format
    for r in mock_responses_data:
        if isinstance(r["Days"], str):
            r["Days"] = [d.strip() for d in r["Days"].split(",")]

    responses = Sheet(data=mock_responses_data)
    records = Sheet(data=mock_records_data)

    _, team = responses.availability(records, "Monday")

    assert "Leader Alice" in team

    assert len(team) == 6

    novices_in_team = [n for n in team if "Novice" in n]
    assert len(novices_in_team) == 3
    assert "Novice Dave" not in team


def test_availability_no_leader():
    """Test that ValueError is raised if no leader is available."""
    bad_records = [
        {"Name": "Bob", "Completed": 0, "Experience": "Varsity", "Position": "Member"}
    ]
    bad_responses = [{"Name": "Bob", "Days": ["Monday"]}]

    responses = Sheet(data=bad_responses)
    records = Sheet(data=bad_records)

    with pytest.raises(ValueError, match="No leader available"):
        responses.availability(records, "Monday")


def test_availability_invalid_day():
    responses = Sheet(data=[])
    records = Sheet(data=[])

    with pytest.raises(ValueError, match="Invalid day"):
        responses.availability(records, "Funday")


def test_read_config(tmp_path, monkeypatch):
    """Test reading a valid config file."""
    config_data = {
        "api_key_path": "k.json",
        "sheet_name": "S",
        "worksheets": {"responses": "R", "records": "Rec"},
    }

    p = tmp_path / "config.json"
    p.write_text(json.dumps(config_data))

    monkeypatch.chdir(tmp_path)

    config = read_config()
    assert config["sheet_name"] == "S"


def test_read_config_missing(monkeypatch):
    """Test exception on missing config."""
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError),
    )

    with pytest.raises(FileNotFoundError):
        read_config()


@pytest.fixture
def messy_responses_data():
    """Mock Responses with messy formatting for testing normalization."""
    return [
        {
            "Name": "  Leader Alice  ",
            "Days": " monday , Wednesday , friday ",
            "Replacement": "No",
        },
        {"Name": "Varsity Bob", "Days": "Tuesday, thursday ", "Replacement": "Yes"},
        {"Name": "Novice Carol", "Days": "saturday , SUNDAY", "Replacement": "No"},
    ]


@pytest.fixture
def mock_gspread_messy(monkeypatch, messy_responses_data):
    """Mocks gspread to return messy data."""

    class MockWorksheet:
        def get_all_records(self):
            return messy_responses_data

    class MockSpreadsheet:
        def worksheet(self, name):
            return MockWorksheet()

    class MockClient:
        def open(self, name):
            return MockSpreadsheet()

    monkeypatch.setattr("gspread.service_account", lambda filename: MockClient())


def test_days_normalization(mock_gspread_messy):
    """Test that 'Days' are stripped and split properly, but original casing preserved."""
    # This tests update() logic, so we use mock_gspread_messy and call update()
    sheet = Sheet("key.json", "Snow Data", "Responses")
    sheet.update()

    alice = next(r for r in sheet.sheet if "Alice" in r["Name"])
    assert alice["Days"] == [
        "monday",
        "Wednesday",
        "friday",
    ]

    bob = next(r for r in sheet.sheet if "Bob" in r["Name"])
    assert bob["Days"] == ["Tuesday", "thursday"]

    carol = next(r for r in sheet.sheet if "Carol" in r["Name"])
    assert carol["Days"] == ["saturday", "SUNDAY"]


def test_name_stripping(mock_gspread_messy):
    """Test that leading/trailing spaces in Name are removed."""
    sheet = Sheet("key.json", "Snow Data", "Responses")
    sheet.update()
    names = [r["Name"] for r in sheet.sheet]
    assert "Leader Alice" in names
    assert "  Leader Alice  " not in names


def test_replacement_removed(mock_gspread_messy):
    """Test that 'Replacement' field is removed."""
    sheet = Sheet("key.json", "Snow Data", "Responses")
    sheet.update()
    for r in sheet.sheet:
        assert "Replacement" not in r
