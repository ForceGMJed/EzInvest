import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/changePassword", methods=["GET", "POST"])
@login_required
def changePassword():

    userID = session["user_id"]

    if request.method == "POST":

       # blank reject

        _password = request.form.get("password")
        if not _password:
            return apology("New Password can not be blank!")

        _passwordConfirmation = request.form.get("passwordConfirmation")
        if not _passwordConfirmation:
            return apology("Confimation can not be blank!")

        # input reject

        if _password != _passwordConfirmation:
            return apology("Password does not match!")

        _hash = generate_password_hash(_password)
        row = db.execute("SELECT hash from users where id = ?", userID)
        if _hash == row[0]["hash"]:
            return apology("Cannot use the same password!")

        ################### PROCEED WITH pw change #####################

        _hash = generate_password_hash(_password)
        db.execute("update users set hash = ? WHERE id = ?", _hash, userID)

        return render_template("changePasswordSuccess.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("changePassword.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

       # blank reject

        _username = request.form.get("username")
        if not _username:
            return apology("Name can not be blank!")

        _password = request.form.get("password")
        if not _password:
            return apology("Password can not be blank!")

        _passwordConfirmation = request.form.get("confirmation")
        if not _passwordConfirmation:
            return apology("Confimation can not be blank!")

        # input reject

        if _password != _passwordConfirmation:
            return apology("Password does not match!")

        rows = db.execute("SELECT EXISTS (SELECT 1 FROM users WHERE username = ?) AS isNewTaken", _username)
        print(rows[0]["isNewTaken"])
        if rows[0]["isNewTaken"] != 0 :
            return apology("Username is taken!")


        ################### PROCEED WITH REGISTER #####################

        _hash = generate_password_hash(_password)
        db.execute("INSERT INTO users(username, hash) VALUES(?,?)",_username, _hash)

        # return apology(f"Username: {_username} , pw: {_password} , hash: {_hash}")

        return render_template("registerSuccess.html", newUserName = _username)



    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    userID = session["user_id"]

    if request.method == "POST":

        # user input
        sym = request.form.get("symbol")
        print(sym)
        if not sym:
            print("WAEOIDBOIUWABOWIUAWOEBAIWOABEIBOIEWA")
            return apology("Invalid symbol!")

        # look up stock info: {"name": symbol, "price": price, "symbol": symbol}
        stockInfo = lookup(sym)
        print(stockInfo)

        if not stockInfo:
            return apology("Stock not found!")

        stockName = stockInfo["name"]
        currentPrice = stockInfo["price"]


        # get user port if exist
        if IsStockExist(userID,stockName):
            portfolioPrice = GetUserStockAvgPrice(userID,stockName)
            porfolioAmount = GetUserStockAmount(userID,stockName)

            if portfolioPrice < currentPrice:
                _isPositiveSell = "TRUE"

            else:
                _isPositiveSell = "FALSE"

            _percentageProfit = abs(round(((currentPrice-portfolioPrice)/portfolioPrice) *100,2))

        else:
            portfolioPrice = 0
            porfolioAmount = 0
            _percentageProfit = 0
            _isPositiveSell = None

        return render_template("quoted.html",quoted = stockInfo, portPrice = portfolioPrice, portAmount = porfolioAmount, isPositiveSell = _isPositiveSell, percentageProfit=_percentageProfit)

    else:
        return render_template("quote.html")

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # session.clear()

    userID = session["user_id"]
    print("userID: " + str(userID))

    _username = GetUsername(userID)

    # if portfolio is completely empty

    if not IsPorfolioExist(userID):
        print(f"user: {_username} have no portfolio")
        return render_template("index_portfolio.html", userCashLeft = GetUserCash(userID), stockTotalValue = 0, username = _username, totalCost = 0, totalValue = 0, grandTotal = GetUserCash(userID), unrealisedTotalGain= 0 )

    # pfo is not empty

    _userPortfolio = GetUserPortfolio(userID)
    _totalCost = GetUserTotalPortfolioCost(_userPortfolio)
    _userCash = GetUserCash(userID)

    # add RT stock prices next to each row of portfolio
    _realTimePorfolio = GetRealTimePorfolio(_userPortfolio)
    _totalValue = GetUserTotalPortfolioValue(_realTimePorfolio)

    # get totalUnrealisedGain in percentage
    _unrealisedTotalGain = round(((_totalValue - _totalCost) / _totalCost) * 100,2)

    #get grandtotal
    _grandTotal = round(_userCash+ _totalValue,2)

    return render_template("index_portfolio.html", userPortfolio =_realTimePorfolio , userCashLeft = _userCash, totalCost = _totalCost, totalValue = _totalValue, username = _username, unrealisedTotalGain= _unrealisedTotalGain,grandTotal = _grandTotal)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    userID = session["user_id"]
    print("session user_id]: "+ str(userID))

    if request.method == "POST":

        # user input
        stockName = request.form.get("symbol")
        buyAmount = request.form.get("shares")

        if not stockName:
            return apology("Invalid symbol!")
        if not buyAmount:
            return apology("Invalid number of shares!")
        if not buyAmount.isdigit():
            return apology("Invalid number of shares!")

        buyAmount = int(buyAmount)

        if buyAmount < 0:
            return apology("Invalid number of shares!")

        stockName = str(stockName)

       # look up stock info: {"name": symbol, "price": price, "symbol": symbol}
        stockInfo = lookup(stockName)
        print(stockInfo)

        if not stockInfo:
            return apology("Stock not found!")


        # currentPrice = stockInfo["price"]
        # stockName = str(stockInfo["name"])

        try :
            currentPrice = stockInfo["price"]

        except TypeError:
            return apology("Invalid number of shares!")

        try :
            stockName = str(stockInfo["name"])

        except TypeError:
            return apology("Stock not found!")

        # get user current avg price of that stock if exist
        if IsStockExist(userID,stockName):
            holdPrice = GetUserStockAvgPrice(userID,stockName)
        else:
            holdPrice = 0

        #handle cash logic
        currentPrice = round(currentPrice,2)
        currentCash = GetUserCash(userID)

        cashNeeded = buyAmount * currentPrice
        cashNeeded = round(cashNeeded,2)

        remainingCash = currentCash - cashNeeded
        remainingCash = round(remainingCash,2)

        print(f"currentcash:{currentCash}, buying: {buyAmount} cashNeeded: {cashNeeded}, remainingCash: {remainingCash}")

        if remainingCash < 0:
            return apology("Not enough cash!")

        ######### proceed with transaction ##########

        # handle db updates
        UpdateUserCash(remainingCash,userID)
        UpdateTransaction(userID , stockName, buyAmount, holdPrice, currentPrice, 0, "BUY")

        # if target stock dont exist
        if not IsStockExist(userID,stockName):
            AddStock(userID , stockName, buyAmount,currentPrice)

        # target stock is already present
        else:
            oldAmount = GetUserStockAmount(userID,stockName)
            oldAvgPrice = GetUserStockAvgPrice(userID,stockName)

            newAvgPrice = (oldAmount * oldAvgPrice + buyAmount * currentPrice)/(oldAmount + buyAmount)
            newAvgPrice = round(newAvgPrice,2)

            print(f"oldAmount: {oldAmount},oldAvgPrice: {oldAvgPrice} => newAvgPrice: {newAvgPrice}")

            UpdatePortfolio_Buy(oldAmount + buyAmount, newAvgPrice, userID, stockName)

        ######## redraw portfolio page ########

        _userPortfolio = GetUserPortfolio(userID)
        _totalCost = GetUserTotalPortfolioCost(_userPortfolio)

        # add RT stock prices next to each row of portfolio
        _realTimePorfolio = GetRealTimePorfolio(_userPortfolio)
        _totalValue = GetUserTotalPortfolioValue(_realTimePorfolio)

        # get totalUnrealisedGain in percentage
        _unrealisedTotalGain = round(((_totalValue - _totalCost) / _totalCost) * 100,2)

        #get grandtotal
        _grandTotal = round(remainingCash+ _totalValue,2)

        return render_template("index_portfolio.html",transactionState = "bought", shareNumber = str(buyAmount), stock = str(stockName), userPortfolio =_realTimePorfolio, userCashLeft = remainingCash, totalCost = _totalCost , totalValue =_totalValue, unrealisedTotalGain= _unrealisedTotalGain,grandTotal = _grandTotal)

    else:
        return render_template("buy.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    userID = session["user_id"]
    print("session user_id]: "+ str(userID))

    if request.method == "POST":

        # user input
        stockName = request.form.get("symbol")
        sellAmount = request.form.get("shares")

        if not stockName:
            return apology("Invalid symbol!")
        if not sellAmount:
            return apology("Invalid number of shares!")
        if not sellAmount.isdigit():
            return apology("Invalid number of shares!")

        sellAmount = int(sellAmount)

        if sellAmount < 0:
            return apology("Invalid number of shares!")

        stockName = str(stockName)

        # look up stock info: {"name": symbol, "price": price, "symbol": symbol}
        stockInfo = lookup(stockName)
        print(stockInfo)

        if not stockInfo:
            return apology("Stock not found!")

        currentPrice = stockInfo["price"]
        stockName = str(stockInfo["name"])
        sellAmount = int(sellAmount)

        # get user current avg price of that stock
        holdPrice = GetUserStockAvgPrice(userID,stockName)

        #handle cash logic

        # target stock doesnt exist
        if not IsStockExist(userID,stockName):
            return apology("You dont have that stock in your portfolio!")

        # target stock doesnot have enough amount to be sold
        currentAmount = GetUserStockAmount( userID,stockName)
        remainAmount = int(currentAmount) - sellAmount
        if remainAmount < 0:
            return apology("You dont have enough stock to sell!")

        ####### proceed with transaction ########

        currentPrice = round(currentPrice,2)
        currentCash = GetUserCash(userID)

        cashGain = sellAmount * currentPrice
        cashGain = round(cashGain,2)
        totalRealisedGainInUSD = (currentPrice - holdPrice) * sellAmount

        remainingCash = currentCash + cashGain
        remainingCash = round(remainingCash,2)

        realisedGain = round((((currentPrice - holdPrice)/ holdPrice) * 100),2)

        print(f"currentcash:{currentCash}, cashGain: {cashGain}, remainingCash: {remainingCash}")

        # handle db updates
        UpdateUserCash(remainingCash,userID)
        UpdateTransaction(userID , stockName, sellAmount, holdPrice, currentPrice, realisedGain, "SELL")

        # no more of that stock
        if remainAmount == 0:
            DeleteStock(userID, stockName)
        else:
            UpdatePortfolio_Sell(remainAmount, userID, stockName)


        # update user lifetime info
        AddUserTotalProfit(userID, totalRealisedGainInUSD)

        ######## redraw portfolio page ########

        _userPortfolio = GetUserPortfolio(userID)
        _totalCost = GetUserTotalPortfolioCost(_userPortfolio)

        # add RT stock prices next to each row of portfolio
        _realTimePorfolio = GetRealTimePorfolio(_userPortfolio)
        _totalValue = GetUserTotalPortfolioValue(_realTimePorfolio)

        # get totalUnrealisedGain in percentage

        ## if portfolio is completely empty, hardcode _unrealisedTotalGain = 0
        if not IsPorfolioExist(userID):
            _unrealisedTotalGain = 0
        else:
            _unrealisedTotalGain = round(((_totalValue - _totalCost) / _totalCost) * 100,2)

        #get grandtotal
        _grandTotal = round(remainingCash+ _totalValue,2)

        return render_template("index_portfolio.html",transactionState = "sold", shareNumber = str(sellAmount), stock = str(stockName), userPortfolio =_realTimePorfolio, userCashLeft = remainingCash, totalCost = _totalCost, totalValue = _totalValue, unrealisedTotalGain= _unrealisedTotalGain, grandTotal = _grandTotal)

    else:
        _userStocksList = GetUserStockNames(userID)
        return render_template("sell.html", userStocksList = _userStocksList)

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    userID = session["user_id"]
    _userRecord = GetUserTransactionRecords(userID)
    _totalTradeVolume = GetTotalVolume(_userRecord)
    _netProfit = GetUserNetProfit(userID)
    return render_template("history.html", userRecord = _userRecord , totalTradeVolume =_totalTradeVolume, netProfit = _netProfit)

@app.route("/sellAll", methods=["POST"])
@login_required
def sellAll():

    userID = session["user_id"]
    print("session user_id]: "+ str(userID))

    totalRealisedGainInUSD = 0
    for stock in GetUserPortfolio(userID):

        # get current price
        stockName = stock["stock"]
        stockInfo = lookup(stockName)
        print(stockInfo)
        currentPrice = stockInfo["price"]
        stockName = str(stockInfo["name"])

        # get amount held of the stock
        sellAmount = GetUserStockAmount( userID,stockName)

        # get user current avg price of that stock
        holdPrice = GetUserStockAvgPrice(userID,stockName)

        ####### proceed with transaction ########

        currentPrice = round(currentPrice,2)
        currentCash = GetUserCash(userID)

        cashGain = sellAmount * currentPrice
        cashGain = round(cashGain,2)
        totalRealisedGainInUSD += (currentPrice - holdPrice) * sellAmount

        remainingCash = currentCash + cashGain
        remainingCash = round(remainingCash,2)

        realisedGain = round((((currentPrice - holdPrice)/ holdPrice) * 100),2)

        UpdateUserCash(remainingCash,userID)
        UpdateTransaction(userID , stockName, sellAmount, holdPrice, currentPrice, realisedGain, "SELL")
        DeleteStock(userID, stockName)
        _transactionState = "soldAll"

    else:
        _transactionState = "empty"

    # update user lifetime info
    AddUserTotalProfit(userID,totalRealisedGainInUSD)

    ######## redraw portfolio page ########

    _userPortfolio = GetUserPortfolio(userID)
    _totalCost = 0
    remainingCash = GetUserCash(userID)
    _totalValue = 0

    # get totalUnrealisedGain in percentage
    _unrealisedTotalGain = 0

    #get grandtotal
    _grandTotal = round(remainingCash+ _totalValue,2)

    return render_template("index_portfolio.html",transactionState = _transactionState, userPortfolio =_userPortfolio, userCashLeft = remainingCash, totalValue = _totalValue, totalCost = _totalCost, unrealisedTotalGain= _unrealisedTotalGain,grandTotal = _grandTotal)

@app.route("/addCash", methods=["POST"])
@login_required
def addCash():
    userID = session["user_id"]
    print("session user_id]: "+ str(userID))

    addAmount = request.form.get("Amount")
    if not addAmount or int(addAmount) < 1:
        return apology("Invalid number of cash to buy!")

    if int(addAmount) > 10000 :
        return apology("Cannot add more than 10k USD at a time!")

    addAmount = int(addAmount)
    newCashAmount = GetUserCash(userID)+addAmount
    UpdateUserCash(newCashAmount,userID)
    UpdateTransaction(userID,"Cash",addAmount,0,0,0,"BUY")

    _userPortfolio = GetUserPortfolio(userID)
    _totalCost = GetUserTotalPortfolioCost(_userPortfolio)

    remainingCash = GetUserCash(userID)
    _transactionState = "addedCash"

    # add RT stock prices next to each row of portfolio
    _realTimePorfolio = GetRealTimePorfolio(_userPortfolio)
    _totalValue = GetUserTotalPortfolioValue(_realTimePorfolio)

    # get totalUnrealisedGain in percentage
    _unrealisedTotalGain = round(((_totalValue - _totalCost) / _totalCost) * 100,2)

    #get grandtotal
    _grandTotal = round(remainingCash+ _totalValue,2)

    return render_template("index_portfolio.html",transactionState = _transactionState, userPortfolio =_realTimePorfolio, userCashLeft = remainingCash, totalValue = _totalValue, totalCost = _totalCost , AddedCashAmount = addAmount, unrealisedTotalGain= _unrealisedTotalGain,grandTotal = _grandTotal)


def GetUserTotalPortfolioValue(_rtPort):
    totalValue = 0
    for stock in _rtPort:
        totalValue = totalValue + stock["realtimePrice"] * stock["amount"]
    return round(totalValue,2)

def GetUserTotalPortfolioCost(_userPortfolio):
    totalValue = 0
    for stock in _userPortfolio:
        totalValue = totalValue + stock["avgPrice"] * stock["amount"]
    return round(totalValue,2)

def GetUserCash(_userID):
    cashRow =  db.execute("SELECT cash FROM users WHERE id = ?", _userID)
    userCash = float(cashRow[0]["cash"])
    return round(userCash,2)

def GetUserPortfolio(_userID):
    return db.execute("SELECT stock, amount, avgPrice FROM portfolios WHERE client_id = ?", _userID)

def GetUsername(_userID):
    row = db.execute("SELECT username FROM users WHERE id = ?", _userID)
    return row[0]["username"]

def UpdateUserCash(_newAmount,_userID):
     db.execute("UPDATE users SET cash = ? WHERE id = ? ",_newAmount, _userID)

def IsStockExist(_userID,_stock):
    row = db.execute("SELECT EXISTS(SELECT 1 FROM portfolios WHERE client_id = ? and stock = ? ) as isStockExist ", _userID,_stock)
    print(row)
    if row[0]["isStockExist"]!=1:
        return False
    else:
       return True

def IsPorfolioExist(_userID):
    row = db.execute("SELECT EXISTS(SELECT 1 FROM portfolios WHERE client_id = ? ) as isPortfolioExist ", _userID)
    print(row)
    if row[0]["isPortfolioExist"]!=1:
        return False
    else:
        return True

def UpdatePortfolio_Buy(_newAmount, _newAvgPrice, _userID, _stock):
    db.execute("UPDATE portfolios SET amount =  ?, avgPrice = ?  WHERE client_id = ? and stock = ? ",_newAmount, _newAvgPrice, _userID, _stock)

def UpdatePortfolio_Sell(_newAmount, _userID, _stock):
    db.execute("UPDATE portfolios SET amount =  ? WHERE client_id = ? and stock = ? ",_newAmount, _userID, _stock)

def DeleteStock(_userID, _stock):
    db.execute("DELETE FROM portfolios WHERE client_id = ? and stock = ? ", _userID, _stock)

def UpdateTransaction(_userID , _stock, _Amount, _holdPrice, _price,_realisedGain,actionType):
    db.execute("INSERT INTO transactions(client_id,stock,amount,holdprice,price,realisedGain,date,action)  VALUES(?,?,?,?,?,?, datetime('now', 'localtime'),?)",_userID , _stock, _Amount, _holdPrice,_price, _realisedGain, actionType)

def AddStock(_userID , _stockName, _buyAmount,_stockPrice):
    db.execute("INSERT INTO portfolios(client_id,stock,amount,avgPrice) VALUES(?,?,?,?)",_userID , _stockName, _buyAmount, _stockPrice)

def GetUserTransactionRecords(_userID):
    return db.execute("SELECT * FROM transactions WHERE client_id = ? ORDER BY date DESC LIMIT 100", _userID)

def GetTotalVolume(_userRecord):
    totatVol = 0
    for trade in _userRecord:
        if trade["price"] == 0:
            continue
        totatVol = totatVol + trade["price"] * trade["amount"]
    return totatVol
def GetUserStockNames(_userID):
    return db.execute("select stock from portfolios where client_id = ?",_userID)

def GetRealTimePorfolio(_userPortfolio):
    _realTimePorfolio =_userPortfolio
    for stock in _realTimePorfolio:
        stockInfo = lookup(stock["stock"])
        currentPrice = stockInfo["price"]
        stock["realtimePrice"] = currentPrice
        portPrice = stock["avgPrice"]
        stock["realisedGain"] = round((((currentPrice - portPrice)/portPrice)*100),2)

    return _realTimePorfolio

def GetUserStockAvgPrice(_userID,_stock):
    row = db.execute("SELECT avgPrice from portfolios where client_id = ? and stock = ?", _userID, _stock )
    return round(row[0]["avgPrice"],2)

def AddUserTotalCost(_userID,_cost):
    db.execute("UPDATE users SET totalCost = totalCost + ? WHERE id = ? ",_cost ,_userID)

def AddUserTotalProfit(_userID,_profit):
    db.execute("UPDATE users SET totalProfit = totalProfit + ? WHERE id = ? ",_profit ,_userID)

def GetUserNetProfit(_userID):
    row = db.execute("select totalProfit from users where id = ?",_userID)
    return row[0]["totalProfit"]

def GetUserStockAmount(_userID,_stock):
    row = db.execute("select amount from portfolios where client_id = ? and stock = ?",_userID,_stock)
    return int(row[0]["amount"])


# CREATE TABLE portfolios (
# client_id integer NOT NULL,
# stock text NOT NULL,
# amount integer NOT NULL,
# avgPrice decimal(7,2) NOT NULL,
# FOREIGN KEY (client_id) REFERENCES users (id)
# )


# CREATE TABLE transactions (
# client_id integer NOT NULL,
# stock text NOT NULL,
# amount integer NOT NULL,
# holdPrice decimal(7,2),
# price decimal(7,2) NOT NULL,
# realisedGain decimal(7,2),
# date date NOT NULL,
# action text NOT NULL,
# FOREIGN KEY (client_id) REFERENCES users (id)
# )

# CREATE TABLE users (
# id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
# username TEXT NOT NULL,
# hash TEXT NOT NULL,
# cash NUMERIC NOT NULL DEFAULT 10000.00,
# totalProfit decimal(7,2) DEFAULT 0,
# totalCost decimal(7,2) DEFAULT 0
# )

# CREATE UNIQUE INDEX username ON users (username)