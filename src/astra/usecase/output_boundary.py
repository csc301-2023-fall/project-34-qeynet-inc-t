from typing import Any


def send_data(output_data: Any) -> Any:
    """
    Sends data to the view.

    Args:
        output_data (list[list]): The data to be sent to the view.
            It represents a table of data, where each row is a list of values.

    Returns:
        list[list]: The data sent to the view.
    """

    headerlist = output_data[-2]

    # For now, just print the data to the console, and return the list of data.
    print(f"\n{headerlist[0]} | {headerlist[1]} | {headerlist[2]}")
    print("---------------------------")

    for row in range(len(output_data) - 2):
        print(
            f"{output_data[row][0]}   |   {output_data[row][1]}   |   "
            f"{output_data[row][2]}"
        )

    print("\n\n")

    return output_data
