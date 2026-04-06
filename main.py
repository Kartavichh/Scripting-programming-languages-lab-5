from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, select, func, DECIMAL
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config import DB_URL
from decimal import Decimal

engine = create_engine(DB_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# === Модели данных ===
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    email = Column(String(100), unique=True)
    accounts = relationship("Account", back_populates="owner")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    account_number = Column(String(50))
    balance = Column(DECIMAL(15, 2), default=0.00)
    owner = relationship("Client", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(DECIMAL(15, 2))
    type = Column(String(10))
    account = relationship("Account", back_populates="transactions")

# === CRUD операции ===
def main():
    Base.metadata.create_all(engine)
    db = Session()
    
    # CREATE
    client = Client(username="ivanov", email="i@bank.com")
    db.add(client)
    db.commit()
    db.refresh(client)
    
    account = Account(client_id=client.id, account_number="40817810000000001234", balance=10000.00)
    db.add(account)
    db.commit()
    
    # READ
    clients = db.scalars(select(Client).where(Client.email.like("%@bank.com"))).all()
    print(f"ORM filter: {[c.username for c in clients]}")
    
    # UPDATE
    account.balance += Decimal('5000.00')
    db.commit()
    
    # DELETE
    db.delete(client)
    db.commit()
    
    # Raw SQL
    with engine.connect() as conn:
        conn.execute(Transaction.__table__.insert().values(
            account_id=account.id, amount=100.00, type="debit"
        ))
        conn.commit()
        count = conn.scalar(select(func.count()).select_from(Transaction.__table__))
        print(f"SQL count: {count}")
    
    # Transaction
    try:
        new_client = Client(username="trx", email="trx@bank.com")
        db.add(new_client)
        db.flush()
        db.add(Account(client_id=new_client.id, account_number="40817810000000009999", balance=1000.00))
        db.commit()
    except:
        db.rollback()
    finally:
        db.close()
    
    print("Done")

if __name__ == "__main__":
    main()