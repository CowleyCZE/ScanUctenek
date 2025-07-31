import pytest
from unittest.mock import patch, MagicMock

# Import the functions to be tested from app.py
from app import save_receipt, delete_receipt

@pytest.fixture
def mock_session_state():
    """
    A fixture that patches st.session_state with a MagicMock.
    MagicMock automatically creates attributes on first access,
    which is perfect for simulating st.session_state.
    """
    with patch('app.st.session_state', new_callable=MagicMock) as mock_state:
        # We need to ensure the 'receipts' attribute exists for the tests.
        # We can initialize it here. If a test needs a different initial
        # state, it can just re-assign it.
        mock_state.receipts = []
        yield mock_state

def test_save_receipt_appends_to_list(mock_session_state):
    """Test that save_receipt correctly appends a new receipt."""
    # The fixture initializes mock_session_state.receipts to []
    assert len(mock_session_state.receipts) == 0

    receipt_data = {'id': 1, 'merchant': 'Test'}

    # Call the function to save the receipt
    success = save_receipt(receipt_data)

    assert success is True
    assert len(mock_session_state.receipts) == 1
    assert mock_session_state.receipts[0] == receipt_data

def test_save_receipt_initializes_list_if_none(mock_session_state):
    """Test that save_receipt works even if 'receipts' is None."""
    # Simulate a state where 'receipts' has been set to None
    mock_session_state.receipts = None

    receipt_data = {'id': 1, 'merchant': 'Test'}
    success = save_receipt(receipt_data)

    assert success is True
    assert len(mock_session_state.receipts) == 1

def test_delete_receipt_removes_from_list(mock_session_state):
    """Test that delete_receipt correctly removes a receipt by index."""
    # Setup initial state for this specific test
    mock_session_state.receipts = [{'id': 1}, {'id': 2}, {'id': 3}]

    assert len(mock_session_state.receipts) == 3

    # Delete the item at index 1
    success = delete_receipt(1)

    assert success is True
    assert len(mock_session_state.receipts) == 2
    # Check that the correct item was removed
    assert mock_session_state.receipts[0] == {'id': 1}
    assert mock_session_state.receipts[1] == {'id': 3}

def test_delete_receipt_invalid_index(mock_session_state):
    """Test that delete_receipt handles an out-of-bounds index gracefully."""
    # Setup initial state
    mock_session_state.receipts = [{'id': 1}]

    # Attempt to delete with an invalid index
    success_too_high = delete_receipt(99)
    success_negative = delete_receipt(-1)

    assert success_too_high is False
    assert success_negative is False
    # The list should not have changed
    assert len(mock_session_state.receipts) == 1
