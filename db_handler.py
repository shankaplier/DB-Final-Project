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
def address_splitter(address: str):
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
    values = (street_number, street_name, city, state, zip_code)

    cur.execute(query, values)
    address_result = cur.fetchall()

    address_sk = 0
    if not address_result:
        query = "SELECT MAX(ca_address_sk) FROM customer_address;"
        cur.execute(query)
        address_sk = cur.fetchone()[0] + 1
        query = "INSERT INTO customer_address(ca_address_sk, ca_street_number, ca_street_name, ca_city, ca_state, ca_zip) VALUES(?, ?, ?, ?, ?, ?)"
        values = (address_sk, street_number, street_name, city, state, zip_code)
        cur.execute(query, values)
        save_changes()
    else:
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
        values = (next_sk, new_customer.customer_id, new_customer.name.strip().split(" ", 1)[0], new_customer.name.strip().split(" ", 1)[1], new_customer.email, address_sk)
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

        query = "SELECT * FROM customer WHERE c_customer_id = ? AND c_customer_id <> ?"
        value = [new_customer.customer_id, original_customer_id]

        cur.execute(query, value)
        result = cur.fetchone()

        if result is None:
            # Continue with editing the original customer
            attribute_dict = dict()
            for attribute in str(new_customer).split("\n"):
                if attribute == "":
                    continue
                key = attribute.strip().split(": ")[0]
                value = attribute.strip().split(": ")[1]
                attribute_dict[key] = value

            if len(attribute_dict) != 0:
                execute_values = []

                for key, value in attribute_dict.items():
                    if key == "Customer ID":
                        query2 += "c_customer_id = ?"
                        execute_values.append(f"{value}")
                    elif key == "Name":
                        first_name, last_name = value.strip().split(" ", 1)[0], value.strip().split(" ", 1)[1]
                        query2 += "c_first_name = ?"
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
                cur.execute(query, execute_values)
                save_changes()
            else:
                print(f"no values have been edited")
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
    value = (item_id,)
    cur.execute(query, value)
    line_num = cur.fetchone()[0]
    if line_num is None:
        line_num = 1
    else:
        line_num = line_num + 1

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

def extract_attributes(filter_attributes) -> dict:
    attribute_dict = dict()
    for attribute in str(filter_attributes).split("\n"):
        if attribute == "":
            continue
        key = attribute.strip().split(": ")[0]
        value = attribute.strip().split(": ")[1]
        attribute_dict[key] = value
    return attribute_dict

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

    attribute_dict = extract_attributes(filter_attributes)

    if len(attribute_dict) == 0 and min_price == -1 and max_price == -1 and min_start_year == -1 and max_start_year == -1:
        return []

    execute_values = []

    query2 = "\nWHERE "
    if min_price != -1 and max_price != -1 and min_price <= max_price:
        query2 += "(i_current_price <= ? AND i_current_price >= ?) AND "
        execute_values.append(f"{max_price}")
        execute_values.append(f"{min_price}")
    elif min_price != -1:
        query2 += "(i_current_price >= ?) AND "
        execute_values.append(f"{min_price}")
    elif max_price != -1:
        query2 += "(i_current_price <= ?) AND "
        execute_values.append(f"{max_price}")

    if min_start_year != -1 and max_start_year != -1 and min_start_year <= max_start_year:
        query2 += "(YEAR(i_rec_start_date) <= ? AND YEAR(i_rec_start_date) >= ?) AND "
        execute_values.append(max_start_year)
        execute_values.append(min_start_year)
    elif min_start_year != -1:
        query2 += "(YEAR(i_rec_start_date) >= ?) AND "
        execute_values.append(min_start_year)
    elif max_start_year != -1:
        query2 += "(YEAR(i_rec_start_date) <= ?) AND "
        execute_values.append(max_start_year)

    for key, value in attribute_dict.items():
        if key == "Item ID":
            if use_patterns:
                query2 += "i_item_id LIKE ?"
            else:
                query2 += "i_item_id = ?"
            execute_values.append(f"{value}")
        elif key == "Product Name":
            if use_patterns:
                query2 += "i_product_name LIKE ?"
            else:
                query2 += "i_product_name = ?"
            execute_values.append(f"{value}")
        elif key == "Brand":
            if use_patterns:
                query2 += "i_brand LIKE ?"
            else:
                query2 += "i_brand = ?"
            execute_values.append(f"{value}")
        elif key == "Category":
            if use_patterns:
                query2 += "i_category LIKE ?"
            else:
                query2 += "i_category = ?"
            execute_values.append(f"{value}")
        elif key == "Manufacturer":
            if use_patterns:
                query2 += "i_manufact LIKE ?"
            else:
                query2 += "i_manufact = ?"
            execute_values.append(f"{value}")
        elif key == "Current Price":
            if min_price == -1 and max_price == -1:
                query2 += "i_current_price = ?"
                execute_values.append(f"{value}")
        elif key == "Start Year":
            if min_start_year == -1 and max_start_year == -1:
                query2 += "YEAR(i_rec_start_date) = ?"
                execute_values.append(f"{value}")
        elif key == "Total number of copies owned":
            query2 += "i_num_owned = ?"
            execute_values.append(f"{value}")
        query2 += " AND "
    query = "SELECT * FROM item" + query2
    query = query[:-5] + ";"
    cur.execute(query, execute_values)
    result = cur.fetchall()
    ans = []
    if not result:
        return []
    else:
        for item in result:
            item_id = item[1]
            item_product_name = item[3]
            item_brand = item[4]
            item_category = item[6]
            item_manufacturer = item[7]
            item_current_price = item[8]
            item_start_year = item[2]
            item_num_owned = item[9]
            if item_id == None:
                item_id = ""
            else:
                item_id = item_id.strip()
            if item_product_name == None:
                item_product_name = ""
            else:
                item_product_name = item_product_name.strip()
            if item_category == None:
                item_category = ""
            else:
                item_category = item_category.strip()
            if item_manufacturer == None:
                item_manufacturer = ""
            else:
                item_manufacturer = item_manufacturer.strip()
            if item_current_price == None:
                item_current_price = ""
            if item_start_year == None:
                item_start_year = ""
            else:
                item_start_year = item_start_year.year
            if item_num_owned == None:
                item_num_owned = ""
            if item_brand == None:
                item_brand = ""
            else:
                item_brand = item_brand.strip()
            ans.append(Item(item_id, item_product_name, item_brand, item_category, item_manufacturer, item_current_price, item_start_year, item_num_owned))
    return ans

#Change the query such that we natural join with customer_address and then filter on the result
def get_filtered_customers(filter_attributes: Customer = None, use_patterns: bool = False) -> list[Customer]:
    """
    Returns a list of Customer objects matching the filters.
    """
    attribute_dict = extract_attributes(filter_attributes)

    if len(attribute_dict) == 0:
        return []

    execute_values = []

    query2 = "\nWHERE "
    for key, value in attribute_dict.items():
        if key == "Customer ID":
            if use_patterns:
                query2 += "c_customer_id LIKE ?"
            else:
                query2 += "c_customer_id = ?"
            execute_values.append(f"{value}")
        #Maybe fix this
        elif key == "Name":
            name_parts = value.strip().split()

            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])

                if use_patterns:
                    query2 += "c_first_name LIKE ? AND c_last_name LIKE ?"
                else:
                    query2 += "c_first_name = ? AND c_last_name = ?"

                execute_values.append(first_name)
                execute_values.append(last_name)

            elif len(name_parts) == 1:
                single_name = name_parts[0]

                if use_patterns:
                    query2 += "(c_first_name LIKE ? OR c_last_name LIKE ?)"
                else:
                    query2 += "(c_first_name = ? OR c_last_name = ?)"

                execute_values.append(single_name)
                execute_values.append(single_name)
        elif key == "Email":
            if use_patterns:
                query2 += "c_email_address LIKE ?"
            else:
                query2 += "c_email_address = ?"
            execute_values.append(f"{value}")

        elif key == "Address":
            street_number, street_name, city, state, zip_code = address_splitter(value)
            if use_patterns:
                query2 += "ca_street_number LIKE ? AND "
                query2 += "ca_street_name LIKE ? AND "
                query2 += "ca_city LIKE ? AND "
                query2 += "ca_state LIKE ? AND "
                query2 += "ca_zip LIKE ?"
            else:
                query2 += "ca_street_number = ? AND "
                query2 += "ca_street_name = ? AND "
                query2 += "ca_city = ? AND "
                query2 += "ca_state = ? AND "
                query2 += "ca_zip = ?"
            execute_values.append(f"{street_number}")
            execute_values.append(f"{street_name}")
            execute_values.append(f"{city}")
            execute_values.append(f"{state}")
            execute_values.append(f"{zip_code}")
        query2 += " AND "
    query = "SELECT * FROM customer JOIN customer_address ON c_current_addr_sk = ca_address_sk" + query2
    query = query[:-5] + ";"
    cur.execute(query, execute_values)
    result = cur.fetchall()
    ans = []
    for item in result:
        customer_id = item[1]
        customer_first_name = item[2]
        customer_last_name = item[3]
        customer_email = item[4]
        customer_street_number = item[7]
        customer_street_name = item[8]
        customer_city = item[9]
        customer_state = item[10]
        customer_zip_code = item[11]
        if customer_id == None:
            customer_id = ""
        else:
            customer_id = customer_id.strip()
        if customer_first_name == None:
            customer_first_name = ""
        else:
            customer_first_name = customer_first_name.strip()
        if customer_last_name == None:
            customer_last_name = ""
        else:
            customer_last_name = customer_last_name.strip()
        if customer_email == None:
            customer_email = ""
        else:
            customer_email = customer_email.strip()
        if customer_street_number == None:
            customer_street_number = ""
        else:
            customer_street_number = customer_street_number.strip()
        if customer_street_name == None:
            customer_street_name = ""
        else:
            customer_street_name = customer_street_name.strip()
        if customer_city == None:
            customer_city = ""
        else:
            customer_city = customer_city.strip()
        if customer_state == None:
            customer_state = ""
        else:
            customer_state = customer_state.strip()
        if customer_zip_code == None:
            customer_zip_code = ""
        else:
            customer_zip_code = customer_zip_code.strip()

        customer_address = customer_street_number + " " + customer_street_name + ", " + customer_city + ", " + customer_state + " " + customer_zip_code
        ans.append(Customer(customer_id, customer_first_name + " " + customer_last_name, customer_address, customer_email))
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
    attribute_dict = extract_attributes(filter_attributes)

    execute_values = []

    if len(attribute_dict) == 0 and min_rental_date == None and max_rental_date == None and min_due_date == None and max_due_date == None:
        return []

    query2 = "\nWHERE "
    if min_rental_date != None and max_rental_date != None and min_rental_date <= max_rental_date:
        query2 += "rental_date <= ? AND rental_date >= ? AND "
        execute_values.append(max_rental_date)
        execute_values.append(min_rental_date)
    elif min_rental_date != None:
        query2 += "rental_date >= ? AND "
        execute_values.append(min_rental_date)
    elif max_rental_date != None:
        query2 += "rental_date <= ? AND "
        execute_values.append(max_rental_date)

    if min_due_date != None and max_due_date != None and min_due_date <= max_due_date:
        query2 += "due_date <= ? AND due_date >= ? AND "
        execute_values.append(max_due_date)
        execute_values.append(min_due_date)
    elif min_due_date != None:
        query2 += "due_date >= ? AND "
        execute_values.append(min_due_date)
    elif max_due_date != None:
        query2 += "due_date <= ? AND "
        execute_values.append(max_due_date)


    for key, value in attribute_dict.items():
        if key == "Item ID":
            query2 += "item_id = ?"
            execute_values.append(f"{value}")
        elif key == "Customer ID":  # Edit this a bit more
            query2 += "customer_id = ?"
            execute_values.append(f"{value}")
        elif key == "Rental Date":
            if max_rental_date == None and min_rental_date == None:
                query2 += "rental_date = ?"
                execute_values.append(value)
        elif key == "Due Date":
            if max_due_date == None and min_due_date == None:
                query2 += "due_date = ?"
                execute_values.append(value)
        query2 += " AND "
    query = "SELECT * FROM rental" + query2
    query = query[:-5] + ";"
    cur.execute(query, execute_values)
    ans = []
    result = cur.fetchall()
    for item in result:
        item_id = item[0]
        customer_id = item[1]
        rental_date = item[2]
        due_date = item[3]
        if item_id == None:
            item_id = ""
        else:
            item_id = item_id.strip()
        if customer_id == None:
            customer_id = ""
        else:
            customer_id = customer_id.strip()
        if rental_date == None:
            rental_date = ""
        if due_date == None:
            due_date = ""
        ans.append(Rental(item_id, customer_id, str(rental_date), str(due_date)))
    return ans

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
    attribute_dict = extract_attributes(filter_attributes)

    if len(attribute_dict) == 0 and min_rental_date == None and max_rental_date == None and min_due_date == None and max_due_date == None and min_return_date == None and max_return_date == None:
        return []

    execute_values = []

    query2 = "\nWHERE "

    if min_rental_date != None and max_rental_date != None and min_rental_date <= max_rental_date:
        query2 += "rental_date <= ? AND rental_date >= ? AND "
        execute_values.append(max_rental_date)
        execute_values.append(min_rental_date)
    elif min_rental_date != None:
        query2 += "rental_date >= ? AND "
        execute_values.append(min_rental_date)
    elif max_rental_date != None:
        query2 += "rental_date <= ? AND "
        execute_values.append(max_rental_date)

    if min_due_date != None and max_due_date != None and min_due_date <= max_due_date:
        query2 += "due_date <= ? AND due_date >= ? AND "
        execute_values.append(max_due_date)
        execute_values.append(min_due_date)
    elif min_due_date != None:
        query2 += "due_date >= ? AND "
        execute_values.append(min_due_date)
    elif max_due_date != None:
        query2 += "due_date <= ? AND "
        execute_values.append(max_due_date)

    if min_return_date != None and max_return_date != None and min_return_date <= max_return_date:
        query2 += "return_date <= ? AND return_date >= ? AND "
        execute_values.append(max_return_date)
        execute_values.append(min_return_date)
    elif min_return_date != None:
        query2 += "return_date >= ? AND "
        execute_values.append(min_return_date)
    elif max_return_date != None:
        query2 += "return_date <= ? AND "
        execute_values.append(max_return_date)

    for key, value in attribute_dict.items():
        if key == "Item ID":
            query2 += "item_id = ?"
            execute_values.append(f"{value}")
        elif key == "Customer ID":  # Edit this a bit more
            query2 += "customer_id = ?"
            execute_values.append(f"{value}")
        elif key == "Rental Date":
            if min_rental_date == None and max_rental_date == None:
                query2 += "rental_date = ?"
                execute_values.append(value)
        elif key == "Due Date":
            if min_due_date == None and max_due_date == None:
                query2 += "due_date = ?"
                execute_values.append(value)
        elif key == "Return Date":
            if min_return_date == None and max_return_date == None:
                query2 += "return_date = ?"
                execute_values.append(value)
        query2 += " AND "
    query = "SELECT * FROM rental_history" + query2
    query = query[:-5] + ";"
    ans = []
    cur.execute(query, execute_values)
    result = cur.fetchall()
    for item in result:
        item_id = item[0]
        customer_id = item[1]
        rental_date = item[2]
        due_date = item[3]
        return_date = item[4]
        if item_id == None:
            item_id = ""
        else:
            item_id = item_id.strip()
        if customer_id == None:
            customer_id = ""
        else:
            customer_id = customer_id.strip()
        if rental_date == None:
            rental_date = ""
        if due_date == None:
            due_date = ""
        if return_date == None:
            return_date = ""
        ans.append(RentalHistory(item_id, customer_id, str(rental_date), str(due_date), str(return_date)))
    return ans


def get_filtered_waitlist(filter_attributes: Waitlist = None,
                          min_place_in_line: int = -1,
                          max_place_in_line: int = -1) -> list[Waitlist]:
    """
    Returns a list of Waitlist objects matching the filters.
    """
    attribute_dict = extract_attributes(filter_attributes)

    execute_values = []

    if len(attribute_dict) == 0 and min_place_in_line == -1 and max_place_in_line == -1:
        return []

    query2 = "\nWHERE "

    if min_place_in_line != -1 and max_place_in_line != -1 and min_place_in_line <= max_place_in_line:
        query2 += "place_in_line <= ? AND place_in_line >= ? AND "
        execute_values.append(max_place_in_line)
        execute_values.append(min_place_in_line)
    elif min_place_in_line != -1:
        query2 += "place_in_line >= ? AND "
        execute_values.append(min_place_in_line)
    elif max_place_in_line != -1:
        query2 += "place_in_line <= ? AND "
        execute_values.append(max_place_in_line)

    for key, value in attribute_dict.items():
        if key == "Item ID":
            query2 += "item_id = ?"
            execute_values.append(f"{value}")
        elif key == "Customer ID":
            query2 += "customer_id = ?"
            execute_values.append(f"{value}")
        elif key == "Place in line":
            if min_place_in_line == -1 and max_place_in_line == -1:
                query2 += "place_in_line = ?"
                execute_values.append(value)
        query2 += " AND "
    query = "SELECT * FROM waitlist" + query2
    query = query[:-5] + ";"
    ans = []
    cur.execute(query, execute_values)
    result = cur.fetchall()
    for item in result:
        item_id = item[0]
        customer_id = item[1]
        place_in_line = item[2]
        if item_id == None:
            item_id = ""
        else:
            item_id = item_id.strip()
        if customer_id == None:
            customer_id = ""
        else:
            customer_id = customer_id.strip()
        if place_in_line == None:
            place_in_line = 0
        ans.append(Waitlist(item_id, customer_id, place_in_line))
    return ans


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

    # raise NotImplementedError("you must implement this function")

