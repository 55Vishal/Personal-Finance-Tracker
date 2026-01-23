import json
import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict
import shutil

class Expense:
    """Represents a single expense with validation."""

    CATEGORIES = [
        'Food & Dining', 'Transportation', 'Entertainment', 'Bills & Utilities',
        'Healthcare', 'Shopping', 'Education', 'Travel', 'Other'
    ]

    def __init__(self, date, amount, category, description):
        self.date = self._validate_date(date)
        self.amount = self._validate_amount(amount)
        self.category = self._validate_category(category)
        self.description = description.strip()

    def _validate_date(self, date_str):
        """Validate and parse date string."""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")

    def _validate_amount(self, amount):
        """Validate amount is positive number."""
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            return round(amount, 2)
        except (ValueError, TypeError):
            raise ValueError("Amount must be a valid positive number.")

    def _validate_category(self, category):
        """Validate category is in allowed list (case-insensitive)."""
        category_stripped = category.strip()
        if not category_stripped:
            raise ValueError("Category cannot be empty.")
        # Case-insensitive matching
        category_lower = category_stripped.lower()
        for cat in self.CATEGORIES:
            if cat.lower() == category_lower:
                return cat  # Return the properly cased version
        raise ValueError(f"Category must be one of: {', '.join(self.CATEGORIES)}")

    def to_dict(self):
        """Convert expense to dictionary for JSON serialization."""
        return {
            'date': self.date.isoformat(),
            'amount': self.amount,
            'category': self.category,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data):
        """Create expense from dictionary."""
        return cls(data['date'], data['amount'], data['category'], data['description'])

    def __str__(self):
        return f"{self.date} | ${self.amount:.2f} | {self.category} | {self.description}"


class ExpenseManager:
    """Manages collection of expenses with CRUD operations."""

    def __init__(self):
        self.expenses = []
        self.budget = {}  # Monthly budgets by category

    def add_expense(self, expense):
        """Add a new expense."""
        self.expenses.append(expense)
        self.expenses.sort(key=lambda x: x.date, reverse=True)

    def remove_expense(self, index):
        """Remove expense by index."""
        if 0 <= index < len(self.expenses):
            removed = self.expenses.pop(index)
            return removed
        raise IndexError("Invalid expense index.")

    def search_expenses(self, query):
        """Search expenses by description or category."""
        query = query.lower()
        return [exp for exp in self.expenses
                if query in exp.description.lower() or query in exp.category.lower()]

    def filter_by_category(self, category):
        """Filter expenses by category."""
        return [exp for exp in self.expenses if exp.category == category]

    def filter_by_date_range(self, start_date, end_date):
        """Filter expenses by date range."""
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        return [exp for exp in self.expenses if start <= exp.date <= end]

    def get_monthly_expenses(self, year, month):
        """Get expenses for specific month."""
        return [exp for exp in self.expenses
                if exp.date.year == year and exp.date.month == month]

    def set_budget(self, category, amount):
        """Set monthly budget for a category."""
        self.budget[category] = float(amount)

    def get_budget_status(self, year, month):
        """Get budget status for the month."""
        monthly_expenses = self.get_monthly_expenses(year, month)
        category_totals = defaultdict(float)

        for exp in monthly_expenses:
            category_totals[exp.category] += exp.amount

        status = {}
        for category, budget in self.budget.items():
            spent = category_totals[category]
            status[category] = {
                'budget': budget,
                'spent': spent,
                'remaining': budget - spent,
                'percentage': (spent / budget * 100) if budget > 0 else 0
            }

        return status


class FileHandler:
    """Handles file operations for data persistence."""

    def __init__(self, data_file='expenses.json', backup_dir='backups'):
        self.data_file = data_file
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def save_expenses(self, expenses):
        """Save expenses to JSON file."""
        try:
            data = [exp.to_dict() for exp in expenses]
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise Exception(f"Error saving expenses: {str(e)}")

    def load_expenses(self):
        """Load expenses from JSON file."""
        if not os.path.exists(self.data_file):
            return []

        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            return [Expense.from_dict(item) for item in data]
        except (json.JSONDecodeError, KeyError) as e:
            raise Exception(f"Error loading expenses: {str(e)}")

    def export_to_csv(self, expenses, filename):
        """Export expenses to CSV file."""
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Date', 'Amount', 'Category', 'Description'])
                for exp in expenses:
                    writer.writerow([exp.date, exp.amount, exp.category, exp.description])
        except Exception as e:
            raise Exception(f"Error exporting to CSV: {str(e)}")

    def import_from_csv(self, filename):
        """Import expenses from CSV file."""
        expenses = []
        try:
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        expense = Expense(
                            row['Date'], row['Amount'], row['Category'], row['Description']
                        )
                        expenses.append(expense)
                    except (ValueError, KeyError) as e:
                        print(f"Skipping invalid row: {e}")
        except FileNotFoundError:
            raise Exception(f"CSV file not found: {filename}")
        except Exception as e:
            raise Exception(f"Error importing from CSV: {str(e)}")

        return expenses

    def create_backup(self):
        """Create a backup of the current data file."""
        if os.path.exists(self.data_file):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_dir, f'expenses_backup_{timestamp}.json')
            shutil.copy2(self.data_file, backup_file)
            return backup_file
        return None

    def restore_backup(self, backup_file):
        """Restore data from a backup file."""
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, self.data_file)
            return True
        return False

    def list_backups(self):
        """List available backup files."""
        if os.path.exists(self.backup_dir):
            return [f for f in os.listdir(self.backup_dir) if f.startswith('expenses_backup_')]
        return []


class Reports:
    """Generates various reports and statistics."""

    def __init__(self, expenses):
        self.expenses = expenses

    def monthly_report(self, year, month):
        """Generate monthly expense report."""
        monthly_expenses = [exp for exp in self.expenses
                           if exp.date.year == year and exp.date.month == month]

        if not monthly_expenses:
            return "No expenses found for this month."

        total = sum(exp.amount for exp in monthly_expenses)
        category_totals = defaultdict(float)

        for exp in monthly_expenses:
            category_totals[exp.category] += exp.amount

        report = f"\n{'='*50}\n"
        report += f"MONTHLY REPORT - {year}-{month:02d}\n"
        report += f"{'='*50}\n\n"
        report += f"Total Expenses: ${total:.2f}\n\n"
        report += "Category Breakdown:\n"
        report += "-" * 30 + "\n"

        for category, amount in sorted(category_totals.items()):
            percentage = (amount / total * 100) if total > 0 else 0
            report += f"{category:<20} ${amount:>8.2f} ({percentage:>5.1f}%)\n"

        report += "\nRecent Expenses:\n"
        report += "-" * 50 + "\n"
        for exp in monthly_expenses[:10]:  # Show last 10
            report += f"{exp}\n"

        return report

    def category_breakdown(self):
        """Generate overall category breakdown."""
        if not self.expenses:
            return "No expenses to analyze."

        category_totals = defaultdict(float)
        total = 0

        for exp in self.expenses:
            category_totals[exp.category] += exp.amount
            total += exp.amount

        report = f"\n{'='*50}\n"
        report += "OVERALL CATEGORY BREAKDOWN\n"
        report += f"{'='*50}\n\n"
        report += f"Total Expenses: ${total:.2f}\n\n"
        report += "Category Breakdown:\n"
        report += "-" * 30 + "\n"

        for category, amount in sorted(category_totals.items()):
            percentage = (amount / total * 100) if total > 0 else 0
            report += f"{category:<20} ${amount:>8.2f} ({percentage:>5.1f}%)\n"

        return report

    def expense_trends(self, months=6):
        """Generate expense trend analysis."""
        if not self.expenses:
            return "No expenses to analyze."

        # Get last N months
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=months*30)

        monthly_totals = defaultdict(float)
        for exp in self.expenses:
            if exp.date >= start_date:
                key = f"{exp.date.year}-{exp.date.month:02d}"
                monthly_totals[key] += exp.amount

        if not monthly_totals:
            return "No expenses in the selected period."

        report = f"\n{'='*50}\n"
        report += f"EXPENSE TRENDS - Last {months} Months\n"
        report += f"{'='*50}\n\n"

        sorted_months = sorted(monthly_totals.keys())
        for month in sorted_months:
            report += f"{month}: ${monthly_totals[month]:.2f}\n"

        return report

    def statistics(self):
        """Generate basic statistics."""
        if not self.expenses:
            return "No expenses to analyze."

        amounts = [exp.amount for exp in self.expenses]
        total = sum(amounts)
        count = len(amounts)
        average = total / count if count > 0 else 0
        max_expense = max(amounts)
        min_expense = min(amounts)

        # Most expensive category
        category_totals = defaultdict(float)
        for exp in self.expenses:
            category_totals[exp.category] += exp.amount

        top_category = max(category_totals.items(), key=lambda x: x[1])

        report = f"\n{'='*50}\n"
        report += "EXPENSE STATISTICS\n"
        report += f"{'='*50}\n\n"
        report += f"Total Expenses: {count}\n"
        report += f"Total Amount: ${total:.2f}\n"
        report += f"Average Expense: ${average:.2f}\n"
        report += f"Largest Expense: ${max_expense:.2f}\n"
        report += f"Smallest Expense: ${min_expense:.2f}\n"
        report += f"Top Category: {top_category[0]} (${top_category[1]:.2f})\n"

        return report

    def simple_visualization(self, category_totals):
        """Create simple text-based bar chart."""
        if not category_totals:
            return "No data to visualize."

        max_amount = max(category_totals.values())
        max_bar_length = 40

        viz = "\nCategory Visualization:\n"
        viz += "-" * 50 + "\n"

        for category, amount in sorted(category_totals.items()):
            bar_length = int((amount / max_amount) * max_bar_length) if max_amount > 0 else 0
            bar = "█" * bar_length
            viz += f"{category:<20} {bar} ${amount:>8.2f}\n"

        return viz


class FinanceTracker:
    """Main application class with menu-driven interface."""

    def __init__(self):
        self.manager = ExpenseManager()
        self.file_handler = FileHandler()
        self.load_data()

    def load_data(self):
        """Load expenses and budget data."""
        try:
            self.manager.expenses = self.file_handler.load_expenses()
            # Load budget if exists
            budget_file = 'budget.json'
            if os.path.exists(budget_file):
                with open(budget_file, 'r') as f:
                    self.manager.budget = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load data: {e}")

    def save_data(self):
        """Save expenses and budget data."""
        try:
            self.file_handler.save_expenses(self.manager.expenses)
            # Save budget
            with open('budget.json', 'w') as f:
                json.dump(self.manager.budget, f)
        except Exception as e:
            print(f"Error saving data: {e}")

    def run(self):
        """Main application loop."""
        print("=" * 60)
        print("          PERSONAL FINANCE TRACKER")
        print("=" * 60)

        while True:
            print("\n" + "=" * 40)
            print("              MAIN MENU")
            print("=" * 40)
            print("1. Add New Expense")
            print("2. View All Expenses")
            print("3. Search Expenses")
            print("4. Generate Monthly Report")
            print("5. View Category Breakdown")
            print("6. Set/Update Budget")
            print("7. Export Data to CSV")
            print("8. Import Data from CSV")
            print("9. View Statistics")
            print("10. Backup/Restore Data")
            print("0. Exit")
            print("=" * 40)

            choice = input("\nEnter your choice (0-10): ").strip()

            try:
                if choice == '1':
                    self.add_expense()
                elif choice == '2':
                    self.view_expenses()
                elif choice == '3':
                    self.search_expenses()
                elif choice == '4':
                    self.generate_monthly_report()
                elif choice == '5':
                    self.view_category_breakdown()
                elif choice == '6':
                    self.set_budget()
                elif choice == '7':
                    self.export_data()
                elif choice == '8':
                    self.import_data()
                elif choice == '9':
                    self.view_statistics()
                elif choice == '10':
                    self.backup_restore()
                elif choice == '0':
                    self.save_data()
                    print("\n" + "=" * 60)
                    print("Thank you for using Personal Finance Tracker!")
                    print("=" * 60)
                    break
                else:
                    print("Invalid choice! Please enter 0-10.")
            except Exception as e:
                print(f"An error occurred: {e}")

    def add_expense(self):
        """Add a new expense with validation."""
        print("\n--- ADD NEW EXPENSE ---")

        try:
            date = input("Enter date (YYYY-MM-DD): ").strip()
            amount = input("Enter amount: ").strip()
            print(f"Available categories: {', '.join(Expense.CATEGORIES)}")
            category = input("Enter category: ").strip()
            description = input("Enter description: ").strip()

            expense = Expense(date, amount, category, description)
            self.manager.add_expense(expense)
            self.save_data()  # Save data immediately after adding expense
            print("Expense added successfully!")

        except ValueError as e:
            print(f"Error: {e}")

    def view_expenses(self):
        """Display all expenses."""
        print("\n--- ALL EXPENSES ---")

        if not self.manager.expenses:
            print("No expenses recorded yet.")
            return

        print(f"Total expenses: {len(self.manager.expenses)}")
        print("\n" + "-" * 80)
        print(f"{'#':<3} {'Date':<12} {'Amount':<10} {'Category':<20} {'Description'}")
        print("-" * 80)

        for i, exp in enumerate(self.manager.expenses, 1):
            print(f"{i:<3} {exp.date} {exp.amount:<10.2f} {exp.category:<20} {exp.description}")

        # Option to remove expense
        while True:
            choice = input("\nEnter expense number to remove (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                break
            try:
                index = int(choice) - 1
                removed = self.manager.remove_expense(index)
                self.save_data()  # Save data immediately after removing expense
                print(f"Removed: {removed}")
                break
            except (ValueError, IndexError):
                print("Invalid expense number.")

    def search_expenses(self):
        """Search expenses by query."""
        print("\n--- SEARCH EXPENSES ---")

        query = input("Enter search term (description or category): ").strip()
        if not query:
            print("Please enter a search term.")
            return

        results = self.manager.search_expenses(query)

        if not results:
            print("No expenses found matching your search.")
            return

        print(f"Found {len(results)} matching expenses:")
        print("\n" + "-" * 80)
        print(f"{'Date':<12} {'Amount':<10} {'Category':<20} {'Description'}")
        print("-" * 80)

        for exp in results:
            print(f"{exp.date} {exp.amount:<10.2f} {exp.category:<20} {exp.description}")

    def generate_monthly_report(self):
        """Generate monthly expense report."""
        print("\n--- MONTHLY REPORT ---")

        try:
            year = int(input("Enter year (YYYY): ").strip())
            month = int(input("Enter month (1-12): ").strip())

            if not (1 <= month <= 12):
                print("Invalid month. Please enter 1-12.")
                return

            reports = Reports(self.manager.expenses)
            report = reports.monthly_report(year, month)
            print(report)

        except ValueError:
            print("Invalid year or month format.")

    def view_category_breakdown(self):
        """Display category breakdown."""
        print("\n--- CATEGORY BREAKDOWN ---")

        reports = Reports(self.manager.expenses)
        report = reports.category_breakdown()
        print(report)

        # Add simple visualization
        category_totals = defaultdict(float)
        for exp in self.manager.expenses:
            category_totals[exp.category] += exp.amount

        viz = reports.simple_visualization(category_totals)
        print(viz)

    def set_budget(self):
        """Set or update budget for categories."""
        print("\n--- SET/UPDATE BUDGET ---")
        print(f"Available categories: {', '.join(Expense.CATEGORIES)}")

        category = input("Enter category: ").strip()
        if category not in Expense.CATEGORIES:
            print("Invalid category.")
            return

        try:
            amount = float(input("Enter monthly budget amount: ").strip())
            if amount <= 0:
                print("Budget must be positive.")
                return

            self.manager.set_budget(category, amount)
            self.save_data()  # Save data immediately after setting budget
            print(f"Budget for {category} set to ${amount:.2f}")

            # Show current budget status
            now = datetime.now()
            status = self.manager.get_budget_status(now.year, now.month)
            if category in status:
                stat = status[category]
                print(f"Current month status: ${stat['spent']:.2f} spent, ${stat['remaining']:.2f} remaining ({stat['percentage']:.1f}%)")

        except ValueError:
            print("Invalid amount format.")

    def export_data(self):
        """Export expenses to CSV."""
        print("\n--- EXPORT DATA ---")

        filename = input("Enter CSV filename (default: expenses.csv): ").strip()
        if not filename:
            filename = "expenses.csv"

        if not filename.endswith('.csv'):
            filename += '.csv'

        try:
            self.file_handler.export_to_csv(self.manager.expenses, filename)
            print(f"Data exported to {filename}")
        except Exception as e:
            print(f"Export failed: {e}")

    def import_data(self):
        """Import expenses from CSV."""
        print("\n--- IMPORT DATA ---")

        filename = input("Enter CSV filename to import: ").strip()
        if not filename:
            print("Please enter a filename.")
            return

        try:
            imported_expenses = self.file_handler.import_from_csv(filename)
            self.manager.expenses.extend(imported_expenses)
            self.manager.expenses.sort(key=lambda x: x.date, reverse=True)
            self.save_data()  # Save data immediately after importing
            print(f"Imported {len(imported_expenses)} expenses from {filename}")
        except Exception as e:
            print(f"Import failed: {e}")

    def view_statistics(self):
        """Display expense statistics."""
        print("\n--- STATISTICS ---")

        reports = Reports(self.manager.expenses)
        stats = reports.statistics()
        print(stats)

        # Show expense trends
        trends = reports.expense_trends()
        print(trends)

    def backup_restore(self):
        """Manage data backups."""
        print("\n--- BACKUP/RESTORE DATA ---")
        print("1. Create Backup")
        print("2. Restore from Backup")
        print("3. List Backups")

        choice = input("Enter choice (1-3): ").strip()

        if choice == '1':
            backup_file = self.file_handler.create_backup()
            if backup_file:
                print(f"Backup created: {backup_file}")
            else:
                print("No data to backup.")

        elif choice == '2':
            backups = self.file_handler.list_backups()
            if not backups:
                print("No backups found.")
                return

            print("Available backups:")
            for i, backup in enumerate(backups, 1):
                print(f"{i}. {backup}")

            try:
                index = int(input("Enter backup number to restore: ").strip()) - 1
                if 0 <= index < len(backups):
                    backup_file = os.path.join(self.file_handler.backup_dir, backups[index])
                    if self.file_handler.restore_backup(backup_file):
                        self.load_data()  # Reload data
                        print("Data restored successfully.")
                    else:
                        print("Restore failed.")
                else:
                    print("Invalid backup number.")
            except ValueError:
                print("Invalid input.") 

        elif choice == '3':
            backups = self.file_handler.list_backups()
            if backups:
                print("Available backups:")
                for backup in backups:
                    print(f"  {backup}")
            else:
                print("No backups found.")

        else:
            print("Invalid choice.")


def main():
    """Main entry point."""
    tracker = FinanceTracker()
    tracker.run()


if __name__ == "__main__":
    main()
