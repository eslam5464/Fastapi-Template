#!/bin/bash

# Prompt the user for the location of the .env file
read -p "Enter the location of the .env file: " env_file_location

# Check if the .env file exists
if [ ! -f "$env_file_location" ]; then
    echo "Error: .env file not found at $env_file_location"
    exit 1
fi

# Read environment variables from the .env file
export $(grep -v '^#' "$env_file_location" | xargs)

menu() {
    while true; do
        clear
        echo "Choose an option:"
        echo "==================================="
        echo "1. Upgrade head"
        echo "2. Add revision"
        echo "3. Downgrade base"
        echo "4. Downgrade to a specific revision"
        echo "5. Exit"
        echo "==================================="

        read -p "Enter your choice number: " choice

        case $choice in
            1)
                echo "# You selected Upgrade head #"

                # Run the alembic upgrade command
                alembic upgrade head

                read -p "Press Enter to continue..."
                ;;
            2)
                echo "# You selected Add revision #"

                read -p "Enter a message: " message

                # Run the alembic command with the provided message
                alembic revision --autogenerate -m "$message"

                read -p "Press Enter to continue..."
                ;;
            3)
                echo "# You selected Downgrade base #"

                # Run the alembic downgrade command
                alembic downgrade base

                read -p "Press Enter to continue..."
                ;;
            4)
                echo "# You selected Downgrade to a specific revision #"

                read -p "Enter the revision ID: " revision_id
                alembic downgrade "$revision_id"

                read -p "Press Enter to continue..."
                ;;
            5)
                echo "Exiting the script"
                exit 0
                ;;
            *)
                echo "Invalid choice. Please enter a valid number..."
                read -p "Press Enter to continue..."
                ;;
        esac
    done
}

# Start the menu
menu
