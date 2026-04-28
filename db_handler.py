from os import minor

from google_crc32c import value

from MARIADB_CREDS import DB_CONFIG
from mariadb import connect
from models.RentalHistory import RentalHistory
from models.Waitlist import Waitlist
from models.Item import Item
from models.Rental import Rental
from models.Customer import Customer
from datetime import date, timedelta


conn = connect(user=DB_CONFIG["username"], password=DB_CONFIG["password"], host=DB_CONFIG["host"],
               database=DB_CONFIG["database"], port=DB_CONFIG["port"])


cur = conn.cursor()


def add_item(new_item: Item = None):
    """
    new_item - An Item object containing a new item to be inserted into the DB in the item table.
        new_item and its attributes will never be None.
    """
    try:
        cur.execute("SELECT MAX(i_item_sk) FROM item")
        max_id = cur.fetchone()[0]

        if max_id is None:
            max_id = 0

        next_sk = max_id + 1

        query = """INSERT INTO item(i_item_sk, i_item_id, i_rec_start_date, i_product_name, i_brand,  i_category, i_manufact, i_current_price, i_num_owned)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        values = (next_sk, new_item.item_id, str(new_item.start_year) + "-01-01", new_item.product_name, new_item.brand, new_item.category, new_item.manufact, new_item.current_price, new_item.num_owned)

        cur.execute(query, values)
        save_changes()
    except Exception as e:
        print(e)

    # raise NotImplementedError("you must implement this function")

# Takes in the address of the customer class and returns the street_number, etc seperated
def address_splitter(address: str) -> str:
    street_number = address.strip().split(",")[0].split(" ")[0]
    street_name = " ".join(address.strip().split(",")[0].split(" ")[1:])
    city = address.strip().split(",")[1].strip()
    state = address.strip().split(",")[2].split(" ")[1]
    zip_code = address.strip().split(",")[2].split(" ")[-1]
    return street_number, street_name, city, state, zip_code

#Check if the given address is in customer_address
#if it is then get the address_sk
#else add the address into customer_address and get it's sk
def customer_address_resolver(new_customer: Customer) -> int:
    query = """SELECT ca_address_sk
            FROM customer_address
            WHERE ca_street_number = ? AND ca_street_name = ? AND ca_city = ? AND ca_state = ? AND ca_zip = ?"""

    street_number, street_name, city, state, zip_code = address_splitter(new_customer.address)
    # print(f"street number: {street_number}, street_name: {street_name}, city: {city}, state: {state}, zip: {zip_code}")
    values = (street_number, street_name, city, state, zip_code)

    cur.execute(query, values)
    address_result = cur.fetchall()
    # print(address_result[0])

    address_sk = 0
    if address_result == []:
        print("No address was found")
        query = "SELECT MAX(ca_address_sk) FROM customer_address;"
        cur.execute(query)
        address_sk = cur.fetchone()[0] + 1
        query = "INSERT INTO customer_address(ca_address_sk, ca_street_number, ca_street_name, ca_city, ca_state, ca_zip) VALUES(?, ?, ?, ?, ?, ?)"
        values = (address_sk, street_number, street_name, city, state, zip_code)
        cur.execute(query, values)
        save_changes()
    else:
        print("Address was found")
        address_sk = address_result[0][0]
    return address_sk

def add_customer(new_customer: Customer = None):
    """
    new_customer - A Customer object containing a new customer to be inserted into the DB in the customer table.
        new_customer and its attributes will never be None.
    """
    try:
        # Grab the current MAX customer_sk from customer
        cur.execute("SELECT MAX(c_customer_sk) FROM customer")
        max_id = cur.fetchone()[0]

        if max_id is None:
            max_id = 0

        next_sk = max_id + 1

        address_sk = customer_address_resolver(new_customer)
        query = """INSERT INTO customer(c_customer_sk, c_customer_id, c_first_name, c_last_name, c_email_address,  c_current_addr_sk)
                    VALUES(?, ?, ?, ?, ?, ?)"""
        values = (next_sk, new_customer.customer_id, new_customer.name.strip().split(" ")[0], new_customer.name.strip().split(" ")[1], new_customer.email, address_sk)
        cur.execute(query, values)
        save_changes()
    except Exception as e:
        print(e)



def edit_customer(original_customer_id: str = None, new_customer: Customer = None):
    """
    original_customer_id - A string containing the customer id for the customer to be edited.
    new_customer - A Customer object containing attributes to update. If an attribute is None, it should not be altered.
    """
    try:
        query1 = """UPDATE customer"""
        query2 = "\nSET "
        query3 = "\nWHERE c_customer_id = ?;"

        query = "SELECT * FROM customer WHERE c_customer_id = ?"
        value = [new_customer.customer_id]

        cur.execute(query, value)
        result = cur.fetchone()

        if result == None:
            # Continue with editing the original customer
            attribute_dict = dict()
            for attribute in str(new_customer).split("\n"):
                if attribute == "":
                    continue
                key = attribute.strip().split(": ")[0]
                value = attribute.strip().split(": ")[1]
                attribute_dict[key] = value

            execute_values = []

            for key, value in attribute_dict.items():
                if key == "Customer ID":
                    query2 += "c_customer_id = ?"
                    execute_values.append(f"{value}")
                elif key == "Name":
                    first_name, last_name = value.strip().split(" ")[0], value.strip().split(" ")[1]
                    print(first_name, last_name)
                    query2 += "c_first_name = ? "
                    execute_values.append(f"{first_name}")
                    query2 += ", c_last_name = ?"
                    execute_values.append(f"{last_name}")
                elif key == "Email":
                    query2 += "c_email_address = ?"
                    execute_values.append(f"{value}")
                elif key == "Address":
                    address_sk = customer_address_resolver(new_customer)
                    query2 += "c_current_addr_sk = ?"
                    execute_values.append(f"{address_sk}")
                query2 += " , "
            query2 = query2[:-3]
            execute_values.append(original_customer_id)
            query = query1 + query2 + query3
            print(query)
            print(execute_values)
            cur.execute(query, execute_values)
            save_changes()
        else:
            #Display error message and quit
            print(f"customer was found with id {new_customer.customer_id}, please enter a unique customer id to edit")
    except Exception as e:
        print(e)

    # raise NotImplementedError("you must implement this function")


def rent_item(item_id: str = None, customer_id: str = None):
    """
    item_id - A string containing the Item ID for the item being rented.
    customer_id - A string containing the customer id of the customer renting the item.
    """

    query = "INSERT INTO rental(item_id, customer_id, rental_date, due_date) VALUES(?, ?, ?, ?)"
    value = (item_id, customer_id, date.today(), date.today()+timedelta(14))
    cur.execute(query, value)
    save_changes()

    # raise NotImplementedError("you must implement this function")


def waitlist_customer(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's new place in line.
    """

    query = "SELECT MAX(place_in_line) FROM waitlist WHERE item_id = ?"
    value = (item_id)
    cur.execute(query, value)
    line_num = cur.fetchone()
    if line_num is None:
        line_num = 1
    else:
        line_num = line_num[0] + 1

    query = "INSERT INTO waitlist(item_id, customer_id, place_in_line) VALUES(?, ?, ?)"
    value = (item_id, customer_id, line_num)
    cur.execute(query, value)
    save_changes()
    return line_num
    # raise NotImplementedError("you must implement this function")

def update_waitlist(item_id: str = None):
    """
    Removes person at position 1 and shifts everyone else down by 1.
    """

    query = "DELETE FROM waitlist WHERE item_id = ? AND place_in_line = ?;"
    values = (item_id, 1)
    cur.execute(query, values)

    query = "UPDATE waitlist SET place_in_line = place_in_line - 1 WHERE item_id = ? AND place_in_line > ?;"
    values = (item_id, 1)
    cur.execute(query, values)
    save_changes()
    # raise NotImplementedError("you must implement this function")


def return_item(item_id: str = None, customer_id: str = None):
    """
    Moves a rental from rental to rental_history with return_date = today.
    """
    query = "SELECT * FROM rental WHERE item_id = ? AND customer_id = ?;"
    value = (item_id, customer_id)
    cur.execute(query, value)
    result = cur.fetchone()
    if result is None:
        print("The user does not exist")
    else:
        query = "INSERT INTO rental_history(item_id, customer_id, rental_date, due_date, return_date) VALUES (?, ?, ?, ?, ?)"
        value = (result[0], result[1], result[2], result[3], date.today())
        cur.execute(query, value)
        save_changes()
        query = "DELETE FROM rental WHERE item_id = ? AND customer_id = ?;"
        value = (item_id, customer_id)
        cur.execute(query, value)
        save_changes()


    # raise NotImplementedError("you must implement this function")


def grant_extension(item_id: str = None, customer_id: str = None):
    """
    Adds 14 days to the due_date.
    """
    query = "SELECT * FROM rental WHERE item_id = ? AND customer_id = ?;"
    value = (item_id, customer_id)
    cur.execute(query, value)
    result = cur.fetchone()
    if result is None:
        print("The user does not exist")
    else:
        new_due_date = result[3] + timedelta(days=14)
        query = "UPDATE rental SET due_date = ? WHERE item_id = ? AND customer_id = ?;"
        value = (new_due_date, item_id, customer_id)
        cur.execute(query, value)
        save_changes()
    # raise NotImplementedError("you must implement this function")

#Test it completely
def get_filtered_items(filter_attributes: Item = None,
                       use_patterns: bool = False,
                       min_price: float = -1,
                       max_price: float = -1,
                       min_start_year: int = -1,
                       max_start_year: int = -1) -> list[Item]:
    """
    Returns a list of Item objects matching the filters.
    """

    attribute_dict = dict()
    for attribute in str(filter_attributes).split("\n"):
        if attribute == "":
            continue
        key = attribute.strip().split(": ")[0]
        value = attribute.strip().split(": ")[1]
        # print(f"key: {key}, value:{value}")
        attribute_dict[key] = value
    # print(attribute_dict)

    execute_values = []

    query2 = "\nWHERE "
    for key, value in attribute_dict.items():
        if (use_patterns):
            if key == "Item ID":
                query2 += "i_item_id LIKE ?"
                execute_values.append(f"%{value}%")
            elif key == "Product Name":
                query2 += "i_product_name LIKE ?"
                execute_values.append(f"%{value}%")
            elif key == "Brand":
                query2 += "i_brand LIKE ?"
                execute_values.append(f"%{value}%")
            elif key == "Category":
                query2 += "i_category LIKE ?"
                execute_values.append(f"%{value}%")
            elif key == "Manufacturer":
                query2 += "i_manufact LIKE ?"
                execute_values.append(f"%{value}%")
            elif key == "CurrentPrice":
                if min_price != None and max_price != None and min_price <= max_price:
                    query2 += "(i_current_price <= ? AND i_current_price >= ?)"
                    execute_values.append(f"{max_price}", f"{min_price}")
                elif min_price != None:
                    query2 += "(i_current_price >= ?)"
                    execute_values.append(f"{min_price}")
                elif max_price != None:
                    query2 += "(i_current_price <= ?)"
                    execute_values.append(f"{max_price}")
                else:
                    query2 += "i_current_price = ?"
                    execute_values.append(f"{value}")
            elif key == "Start Year":
                if min_start_year != None and max_start_year != None and min_start_year <= max_start_year:
                    query2 += "(i_rec_start_date <= ? AND i_rec_start_date >= ?)"
                    execute_values = (max_start_year, min_start_year)
                elif min_start_year != None:
                    query2 += "(i_rec_start_date >= ?)"
                    execute_values = (min_start_year)
                elif max_start_year != None:
                    query2 += "(i_rec_start_date <= ?)"
                    execute_values = (max_start_year)
                else:
                    query2 += "i_rec_start_date = ?"
                    execute_values.append(f"{value}")
            elif key == "Total number of copies owned":
                query2 += "i_num_owned = ?"
                execute_values.append(f"{value}")
        else:
            if key == "Item ID":
                query2 += "i_item_id = ?"
                execute_values.append(f"{value}")
            elif key == "Product Name":
                query2 += "i_product_name = ?"
                execute_values.append(f"{value}")
            elif key == "Brand":
                query2 += "i_brand = ?"
                execute_values.append(f"{value}")
            elif key == "Category":
                query2 += "i_category = ?"
                execute_values.append(f"{value}")
            elif key == "Manufacturer":
                query2 += "i_manufact = ?"
                execute_values.append(f"{value}")
            elif key == "CurrentPrice":
                if min_price != None and max_price != None and min_price <= max_price:
                    query2 += "(i_current_price <= ? AND i_current_price >= ?)"
                    execute_values.append(f"{max_price}", f"{min_price}")
                elif min_price != None:
                    query2 += "(i_current_price >= ?)"
                    execute_values.append(f"{min_price}")
                elif max_price != None:
                    query2 += "(i_current_price <= ?)"
                    execute_values.append(f"{max_price}")
                else:
                    query2 += "i_current_price = ?"
                    execute_values.append(f"{value}")
            elif key == "Start Year":
                if min_start_year != None and max_start_year != None and min_start_year <= max_start_year:
                    query2 += "(i_rec_start_date <= ? AND i_rec_start_date >= ?)"
                    execute_values = (max_start_year, min_start_year)
                elif min_start_year != None:
                    query2 += "(i_rec_start_date >= ?)"
                    execute_values = (min_start_year)
                elif max_start_year != None:
                    query2 += "(i_rec_start_date <= ?)"
                    execute_values = (max_start_year)
                else:
                    query2 += "i_rec_start_date = ?"
                    execute_values.append(f"{value}")
                execute_values.append(f"{value}")
            elif key == "Total number of copies owned":
                query2 += "i_num_owned = ?"
                execute_values.append(f"{value}")
        query2 += " AND "
    query = "SELECT * FROM item" + query2
    query = query[:-5] + ";"
    # print(query)
    cur.execute(query, execute_values)
    result = cur.fetchall()
    if result == []:
        print("No results were found")
    else:
        for row in result:
            print(str(row))
        ans = [Item(item[1], item[3], item[4], item[6], item[7], item[8], str(item[2].today().year), item[9]) for item in result]
    # print(type(ans))
    # for item in ans:
        # print(str(item))
    # raise NotImplementedError("you must implement this function")
    return ans

# Fix the address instead of number give actual address? will think about it later
def get_filtered_customers(filter_attributes: Customer = None, use_patterns: bool = False) -> list[Customer]:
    """
    Returns a list of Customer objects matching the filters.
    """
    attribute_dict = dict()
    for attribute in str(filter_attributes).split("\n"):
        if attribute == "":
            continue
        key = attribute.strip().split(": ")[0]
        value = attribute.strip().split(": ")[1]
        # print(f"key: {key}, value:{value}")
        attribute_dict[key] = value
    # print(attribute_dict)

    execute_values = []

    query2 = "\nWHERE "
    for key, value in attribute_dict.items():
        if (use_patterns):
            if key == "Customer ID":
                query2 += "c_customer_id LIKE ?"
                execute_values.append(f"%{value}%")
            elif key == "Name":
                first_name, last_name = value.strip().split(" ")[0], value.strip().split(" ")[1]
                print(first_name, last_name)
                query2 += "c_first_name LIKE ?"
                execute_values.append(f"%{first_name}%")
                query2 += "c_last_name LIKE ?"
                execute_values.append(f"%{last_name}%")
            elif key == "Email":
                query2 += "c_email_address LIKE ?"
                execute_values.append(f"%{value}%")
            elif key == "Address":
                query2 += "c_current_addr_sk = ?"
                execute_values.append(f"{customer_address_resolver(filter_attributes)}")
        else:
            if key == "Customer ID":
                query2 += "c_customer_id = ?"
                execute_values.append(f"{value}")
            elif key == "Name":
                first_name, last_name = value.strip().split(" ")[0], value.strip().split(" ")[1]
                print(first_name, last_name)
                query2 += "c_first_name = ?"
                execute_values.append(f"{first_name}")
                query2 += "c_last_name = ?"
                execute_values.append(f"{last_name}")
            elif key == "Email":
                query2 += "c_email_address = ?"
                execute_values.append(f"{value}")
            elif key == "Address":
                query2 += "c_current_addr_sk = ?"
                execute_values.append(f"{customer_address_resolver(filter_attributes)}")
        query2 += " AND "
    query = "SELECT * FROM customer" + query2
    query = query[:-5] + ";"
    # print(query)
    cur.execute(query, execute_values)
    ans = [Customer(item[1], item[2] +" " + item[3], item[5], item[4]) for item in cur.fetchall()]
    # print(type(ans))
    for item in ans:
        print(str(item))
    return ans

#Modify to add filtering based on dates
def get_filtered_rentals(filter_attributes: Rental = None,
                         min_rental_date: str = None,
                         max_rental_date: str = None,
                         min_due_date: str = None,
                         max_due_date: str = None) -> list[Rental]:
    """
    Returns a list of Rental objects matching the filters.
    """
    attribute_dict = dict()
    for attribute in str(filter_attributes).split("\n"):
        if attribute == "":
            continue
        key = attribute.strip().split(": ")[0]
        value = attribute.strip().split(": ")[1]
        # print(f"key: {key}, value:{value}")
        attribute_dict[key] = value
    # print(attribute_dict)

    execute_values = []

    query2 = "\nWHERE "
    for key, value in attribute_dict.items():
        if key == "Item ID":
            query2 += "item_id = ?"
            execute_values.append(f"{value}")
        elif key == "Customer ID":  # Edit this a bit more
            query2 += "customer_id = ?"
            execute_values.append(f"{value}")
        elif key == "Rental Date":
            if min_rental_date != None and max_rental_date != None and min_rental_date <= max_rental_date:
                query2 += "rental_date <= ? AND rental_date >= ?"
                execute_values.append(max_rental_date, min_rental_date)
            elif min_rental_date != None:
                query2 += "rental_date >= ?"
                execute_values.append(min_rental_date)
            elif max_rental_date != None:
                query2 += "rental_date <= ?"
                execute_values.append(max_rental_date)
            else:
                query2 += "rental_date = ?"
                execute_values.append(value)
        elif key == "Due Date":
            if min_due_date != None and max_due_date != None and min_due_date <= max_due_date:
                query2 += "due_date <= ? AND due_date >= ?"
                execute_values.append(max_due_date, min_due_date)
            elif min_due_date != None:
                query2 += "due_date >= ?"
                execute_values.append(min_due_date)
            elif max_due_date != None:
                query2 += "due_date <= ?"
                execute_values.append(max_due_date)
            else:
                query2 += "due_date = ?"
                execute_values.append(value)
        query2 += " AND "
    query = "SELECT * FROM rental" + query2
    query = query[:-5] + ";"
    # print(query)
    cur.execute(query, execute_values)
    ans = [Rental(item[0], item[1], str(item[2]), str(item[3])) for item in cur.fetchall()]
    # print(type(ans))
    # for item in ans:
    #     print(str(item))
    return ans
    # raise NotImplementedError("you must implement this function")


def get_filtered_rental_histories(filter_attributes: RentalHistory = None,
                                  min_rental_date: str = None,
                                  max_rental_date: str = None,
                                  min_due_date: str = None,
                                  max_due_date: str = None,
                                  min_return_date: str = None,
                                  max_return_date: str = None) -> list[RentalHistory]:
    """
    Returns a list of RentalHistory objects matching the filters.
    """
    attribute_dict = dict()
    for attribute in str(filter_attributes).split("\n"):
        if attribute == "":
            continue
        key = attribute.strip().split(": ")[0]
        value = attribute.strip().split(": ")[1]
        # print(f"key: {key}, value:{value}")
        attribute_dict[key] = value
    # print(attribute_dict)

    execute_values = []

    query2 = "\nWHERE "
    for key, value in attribute_dict.items():
        if key == "Item ID":
            query2 += "item_id = ?"
            execute_values.append(f"{value}")
        elif key == "Customer ID":  # Edit this a bit more
            query2 += "customer_id = ?"
            execute_values.append(f"{value}")
        elif key == "Rental Date":
            if min_rental_date != None and max_rental_date != None and min_rental_date <= max_rental_date:
                query2 += "rental_date <= ? AND rental_date >= ?"
                execute_values.append(max_rental_date, min_rental_date)
            elif min_rental_date != None:
                query2 += "rental_date >= ?"
                execute_values.append(min_rental_date)
            elif max_rental_date != None:
                query2 += "rental_date <= ?"
                execute_values.append(max_rental_date)
            else:
                query2 += "rental_date = ?"
                execute_values.append(value)
        elif key == "Due Date":
            if min_due_date != None and max_due_date != None and min_due_date <= max_due_date:
                query2 += "due_date <= ? AND due_date >= ?"
                execute_values.append(max_due_date, min_due_date)
            elif min_due_date != None:
                query2 += "due_date >= ?"
                execute_values.append(min_due_date)
            elif max_due_date != None:
                query2 += "due_date <= ?"
                execute_values.append(max_due_date)
            else:
                query2 += "due_date = ?"
                execute_values.append(value)
        elif key == "Return Date":
            if min_return_date != None and max_return_date != None and min_return_date <= max_return_date:
                query2 += "return_date <= ? AND return_date >= ?"
                execute_values.append(max_return_date, min_return_date)
            elif min_return_date != None:
                query2 += "return_date >= ?"
                execute_values.append(min_return_date)
            elif max_return_date != None:
                query2 += "return_date <= ?"
                execute_values.append(max_return_date)
            else:
                query2 += "return_date = ?"
                execute_values.append(value)
        query2 += " AND "
    query = "SELECT * FROM rental_history" + query2
    query = query[:-5] + ";"
    # print(query)
    cur.execute(query, execute_values)
    ans = [RentalHistory(item[0], item[1], str(item[2]), str(item[3]), str(item[4])) for item in cur.fetchall()]
    # print(type(ans))
    # for item in ans:
    #     print(str(item))
    return ans
    # raise NotImplementedError("you must implement this function")


def get_filtered_waitlist(filter_attributes: Waitlist = None,
                          min_place_in_line: int = -1,
                          max_place_in_line: int = -1) -> list[Waitlist]:
    """
    Returns a list of Waitlist objects matching the filters.
    """
    attribute_dict = dict()
    for attribute in str(filter_attributes).split("\n"):
        if attribute == "":
            continue
        key = attribute.strip().split(": ")[0]
        value = attribute.strip().split(": ")[1]
        # print(f"key: {key}, value:{value}")
        attribute_dict[key] = value
    # print(attribute_dict)

    execute_values = []

    query2 = "\nWHERE "
    for key, value in attribute_dict.items():
        if key == "Item ID":
            query2 += "item_id = ?"
            execute_values.append(f"{value}")
        elif key == "Customer ID":
            query2 += "customer_id = ?"
            execute_values.append(f"{value}")
        elif key == "Place in line":
            if min_place_in_line != -1 and max_place_in_line != -1 and min_place_in_line <= max_place_in_line:
                query2 += "place_in_line <= ? AND place_in_line >= ?"
                execute_values.append(max_place_in_line, min_place_in_line)
            elif min_place_in_line != -1:
                query2 += "place_in_line >= ?"
                execute_values.append(min_place_in_line)
            elif max_place_in_line != -1:
                query2 += "place_in_line <= ?"
                execute_values.append(max_place_in_line)
            else:
                query2 += "place_in_line = ?"
                execute_values.append(value)
        query2 += " AND "
    query = "SELECT * FROM waitlist" + query2
    query = query[:-5] + ";"
    # print(query)
    cur.execute(query, execute_values)
    ans = [Waitlist(item[0], item[1], str(item[2])) for item in cur.fetchall()]
    # print(type(ans))
    # for item in ans:
    #     print(str(item))
    return ans
    # raise NotImplementedError("you must implement this function")


def number_in_stock(item_id: str = None) -> int:
    """
    Returns num_owned - active rentals. Returns -1 if item doesn't exist.
    """

    query = "SELECT i_num_owned FROM item WHERE i_item_id = ?"
    value = [item_id]
    cur.execute(query, value)
    item = cur.fetchone()
    if item is None:
        return -1
    else:
        query = "SELECT COUNT(*) FROM rental WHERE item_id = ?"
        value = [item_id]
        cur.execute(query, value)
        num_in_rental = cur.fetchone()[0]
        return item[0] - num_in_rental
    # raise NotImplementedError("you must implement this function")


def place_in_line(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's place_in_line, or -1 if not on waitlist.
    """
    query = "SELECT place_in_line FROM waitlist WHERE item_id = ? AND customer_id = ?"
    value = [item_id, customer_id]
    cur.execute(query, value)
    item = cur.fetchone()
    if item is None:
        return -1
    else:
        return item[0]

    # raise NotImplementedError("you must implement this function")


def line_length(item_id: str = None) -> int:
    """
    Returns how many people are on the waitlist for this item.
    """
    query = "SELECT COUNT(*) FROM waitlist WHERE item_id = ?"
    value = [item_id]
    cur.execute(query, value)
    ans = cur.fetchone()[0]
    return ans
    # raise NotImplementedError("you must implement this function")


def save_changes():
    """
    Commits all changes made to the db.
    """
    conn.commit()
    # raise NotImplementedError("you must implement this function")


def close_connection():
    """
    Closes the cursor and connection.
    """
    save_changes()
    cur.close()
    conn.close()
    exit()

    # raise NotImplementedError("you must implement this function")

