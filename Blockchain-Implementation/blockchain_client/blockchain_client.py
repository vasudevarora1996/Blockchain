from collections import OrderedDict
import binascii
import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import requests
from flask import Flask, jsonify, request, render_template
public_key1 = ""
def dbconnect():
	import mysql.connector
	mydb = mysql.connector.connect(
		host="127.0.0.1",
		user="root",
		password="root1234")
	mycursor = mydb.cursor()
	mycursor.execute("CREATE DATABASE IF NOT EXISTS BLOCKCHAIN")
	mycursor.execute("USE BLOCKCHAIN")
	mycursor.execute("CREATE TABLE IF NOT EXISTS WALLET_BALANCE(ID INT AUTO_INCREMENT PRIMARY KEY, PUBLIC_KEY VARCHAR(512), BALANCE INT)")
	return mydb


class Transaction:

    def __init__(self, sender_address, sender_private_key, recipient_address, value):
        self.sender_address = sender_address
        self.sender_private_key = sender_private_key
        self.recipient_address = recipient_address
        self.value = value

    def __getattr__(self, attr):
        return self.data[attr]

    def to_dict(self):
        return OrderedDict({'sender_address': self.sender_address,
                            'recipient_address': self.recipient_address,
                            'value': self.value})

    def sign_transaction(self):
        private_key = RSA.importKey(binascii.unhexlify(self.sender_private_key))
        signer = PKCS1_v1_5.new(private_key)
        h = SHA.new(str(self.to_dict()).encode('utf8'))
        return binascii.hexlify(signer.sign(h)).decode('ascii')

app = Flask(__name__)

@app.route('/')
def index():
	return render_template('./index.html')

@app.route('/make/transaction')
def make_transaction():
	return render_template('./make_transaction.html')

@app.route('/view/transactions')
def view_transaction():
	return render_template('./view_transactions.html')

@app.route('/check/balance', methods=['GET'])
def check_balance():
	global public_key1
	mydb = dbconnect()
	mycursor = mydb.cursor()
	sql = """SELECT BALANCE FROM WALLET_BALANCE WHERE PUBLIC_KEY = %s"""
	val = public_key1
	mycursor.execute(sql, (val, ))
	records = mycursor.fetchone()
	response = {
		'wallet_balance': str(records[0])
    }
	return jsonify(response), 200

@app.route('/wallet/new', methods=['GET'])
def new_wallet():
	global public_key1
	mydb = dbconnect()
	mycursor = mydb.cursor()
	random_gen = Crypto.Random.new().read
	private_key = RSA.generate(1024, random_gen)
	public_key = private_key.publickey()
	public_key1 = binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii')
	sql = """INSERT INTO WALLET_BALANCE (PUBLIC_KEY, BALANCE) VALUES (%s, %s)"""
	val = [binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii'), 10000]
	mycursor.execute(sql, val)
	mydb.commit()
	response = {
		'private_key': binascii.hexlify(private_key.exportKey(format='DER')).decode('ascii'),
		'public_key': binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii')
	}
	return jsonify(response), 200

@app.route('/generate/transaction', methods=['POST'])
def generate_transaction():
	mydb = dbconnect()
	mycursor = mydb.cursor()
	sender_address = request.form['sender_address']
	sender_private_key = request.form['sender_private_key']
	recipient_address = request.form['recipient_address']
	value = request.form['amount']

	sql = """SELECT BALANCE FROM WALLET_BALANCE WHERE PUBLIC_KEY = %s"""
	val = sender_address
	mycursor.execute(sql, (val, ))
	records = mycursor.fetchall()
	y = 0
	for x in records:
		y = x[0]
	sender_balance = int(y) - int(value)
	sql = """UPDATE WALLET_BALANCE SET BALANCE = %s WHERE PUBLIC_KEY = %s"""
	val = [sender_balance, sender_address]
	mycursor.execute(sql, val)
	mydb.commit()
    
	sql = """SELECT BALANCE FROM WALLET_BALANCE WHERE PUBLIC_KEY = %s"""
	val = recipient_address
	mycursor.execute(sql, (val, ))
	records = mycursor.fetchone()
	recipient_balance = int(records[0]) + int(value)
	sql = """UPDATE WALLET_BALANCE SET BALANCE = %s WHERE PUBLIC_KEY = %s"""
	val = [recipient_balance, recipient_address]
	mycursor.execute(sql, val)
	mydb.commit()

	transaction = Transaction(sender_address, sender_private_key, recipient_address, value)
	response = {'transaction': transaction.to_dict(), 'signature': transaction.sign_transaction()}
	return jsonify(response), 200

if __name__ == '__main__':
    from argparse import ArgumentParser
    mydb = dbconnect()
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=8080, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port
    app.run(host='127.0.0.1', port=port)