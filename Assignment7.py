import pymssql

def connect_to_db():
    try:
        conn = pymssql.connect(
            host='cypress.csil.sfu.ca',
            user='s_dmt9',
            password='MQ3YR7bMfA37PEQ6',
            database='dmt9354'
        )
        return conn
    except pymssql.InterfaceError:
        print("Could not connect to the database. Please check your credentials.")
        return None

def login(conn):
    user_id = input("Enter your user ID: ").strip()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_yelp WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    if user:
        print(f"Welcome, {user[1]}!")  # Assuming 'name' is the second column
        return user_id
    else:
        print("Invalid user ID.")
        return None

def main_menu():
    print("\nMain Menu:")
    print("1. Search Business")
    print("2. Search Users")
    print("3. Make Friend")
    print("4. Review Business")
    print("5. Exit")
    choice = input("Enter your choice: ").strip()
    return choice

def search_business(conn):
    min_stars_input = input("Enter minimum number of stars: ").strip()
    try:
        min_stars = float(min_stars_input) if min_stars_input else 0.0
    except ValueError:
        print("Invalid input for minimum stars. Defaulting to 0.0.")
        min_stars = 0.0
    
    city = input("Enter city: ").strip()
    city = f'%{city}%' if city else '%'
    
    name = input("Enter business name (or part of the name): ").strip()
    name = f'%{name}%' if name else '%'
    
    print("\nOrder by:")
    print("1. Name")
    print("2. City")
    print("3. Number of stars")
    order_choice = input("Enter your choice: ").strip()
    order_options = {'1': 'name', '2': 'city', '3': 'stars'}
    order_by = order_options.get(order_choice, 'name')

    cursor = conn.cursor()
    query = f"""
        SELECT business_id, name, address, city, stars
        FROM business
        WHERE stars >= %s AND LOWER(city) LIKE LOWER(%s) AND LOWER(name) LIKE LOWER(%s)
        ORDER BY {order_by}
    """
    cursor.execute(query, (min_stars, city, name))
    results = cursor.fetchall()
    if results:
        print("\nSearch Results:")
        for row in results:
            print(f"ID: {row[0]}, Name: {row[1]}, Address: {row[2]}, City: {row[3]}, Stars: {row[4]}")
    else:
        print("No businesses found matching the criteria.")


def search_users(conn):
    name = input("Enter user name (or part of the name): ").strip()
    name = f'%{name}%' if name else '%'

    min_review_count = input("Enter minimum review count: ").strip()
    try:
        min_reviews = float(min_review_count) if min_review_count else 0.0
    except ValueError:
        print("Invalid input for minimum stars. Defaulting to 0.0.")
        min_reviews = 0.0

    min_avg_stars = input("Enter minimum average stars: ").strip()
    try:
        min_avg = float(min_avg_stars) if min_avg_stars else 0.0
    except ValueError:
        print("Invalid input for minimum stars. Defaulting to 0.0.")
        min_avg = 0.0
    cursor = conn.cursor()
    query = """
        SELECT user_id, name, review_count, useful, funny, cool, average_stars, yelping_since
        FROM user_yelp
        WHERE LOWER(name) LIKE LOWER(%s) AND review_count >= %s AND average_stars >= %s
        ORDER BY name
    """
    cursor.execute(query, (name, min_reviews, min_avg))
    results = cursor.fetchall()
    if results:
        print("\nSearch Results:")
        for row in results:
            print(f"ID: {row[0]}, Name: {row[1]}, Review Count: {row[2]}, Useful: {row[3]}, "
                  f"Funny: {row[4]}, Cool: {row[5]}, Average Stars: {row[6]}, Yelping Since: {row[7]}")
    else:
        print("No users found matching the criteria.")

def make_friend(conn, user_id):
    friend_id = input("Enter the user ID of the person you want to add as a friend: ").strip()
    cursor = conn.cursor()
    # Check if the friend exists
    cursor.execute("SELECT * FROM user_yelp WHERE user_id = %s", (friend_id,))
    friend = cursor.fetchone()
    if friend:
        # Add friendship
        try:
            # Update table and column names
            cursor.execute("INSERT INTO friendship (user_id, friend) VALUES (%s, %s)", (user_id, friend_id))
            conn.commit()
            print(f"You are now friends with {friend[1]}!")
        except pymssql.IntegrityError:
            print("You are already friends with this user.")
    else:
        print("The user ID you entered does not exist.")

def review_business(conn, user_id):
    business_id = input("Enter the business ID you want to review: ").strip()
    cursor = conn.cursor()
    # Check if the business exists
    cursor.execute("SELECT * FROM business WHERE business_id = %s", (business_id,))
    business = cursor.fetchone()
    if business:
        # Constraint: Check if the user has at least one friend who has reviewed the business
        cursor.execute("""
            SELECT 1
            FROM friendship f
            JOIN review r ON f.friend = r.user_id
            WHERE f.user_id = %s AND r.business_id = %s
        """, (user_id, business_id))
        friend_review = cursor.fetchone()
        if friend_review:
            # Proceed to collect stars and submit the review
            stars = input("Enter the number of stars (1-5): ").strip()
            # Validate stars
            if stars.isdigit() and 1 <= int(stars) <= 5:
                try:
                    # Constraint a): Check if the user has already reviewed this business
                    cursor.execute("""
                        SELECT * FROM review WHERE user_id = %s AND business_id = %s
                    """, (user_id, business_id))
                    existing_review = cursor.fetchone()
                    if existing_review:
                        # Update the existing review
                        cursor.execute("""
                            UPDATE review
                            SET stars = %s, useful = 0, funny = 0, cool = 0, date = GETDATE()
                            WHERE review_id = %s
                        """, (stars, existing_review[0]))  # existing_review[0] is review_id
                    else:
                        # Insert new review
                        cursor.execute("""
                            INSERT INTO review (review_id, user_id, business_id, stars, useful, funny, cool, date)
                            VALUES (NEWID(), %s, %s, %s, 0, 0, 0, GETDATE())
                        """, (user_id, business_id, stars))
                    conn.commit()
                    print("Your review has been submitted.")
                    # Update the business's stars and review count
                    update_business_stars_and_review_count(conn, business_id)
                except pymssql.IntegrityError as e:
                    print("An error occurred while submitting your review:", e)
            else:
                print("Invalid number of stars. Please enter an integer between 1 and 5.")
        else:
            print("You cannot review this business because you have no friends who have reviewed it.")
    else:
        print("The business ID you entered does not exist.")

def update_business_stars_and_review_count(conn, business_id):
    cursor = conn.cursor()
    # Calculate the latest review from each user for the business
    cursor.execute("""
        WITH LatestReviews AS (
            SELECT user_id, stars,
                   ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY date DESC) AS rn
            FROM review
            WHERE business_id = %s
        )
        SELECT AVG(stars), COUNT(*)
        FROM LatestReviews
        WHERE rn = 1
    """, (business_id,))
    avg_stars, review_count = cursor.fetchone()
    # Update the business table
    cursor.execute("""
        UPDATE business
        SET stars = %s, review_count = %s
        WHERE business_id = %s
    """, (avg_stars, review_count, business_id))
    conn.commit()

def main():
    conn = connect_to_db()
    if conn is None:
        return
    user_id = None
    try:
        conn.autocommit(False)  
        user_id = None
        while user_id is None:
            user_id = login(conn)
        while True:
            choice = main_menu()
            if choice == '1':
                search_business(conn)
            elif choice == '2':
                search_users(conn)
            elif choice == '3':
                make_friend(conn, user_id)
            elif choice == '4':
                review_business(conn, user_id)
            elif choice == '5':
                print("Exiting and rolling back any changes made...")
                conn.rollback()  # Rollback all changes
                conn.close()
                break
            else:
                print("Invalid choice. Please try again.")
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()  
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
