from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, select, func, DECIMAL, Table
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
    
    # Связь 1:1
    profile = relationship("ClientProfile", back_populates="client", uselist=False, cascade="all, delete-orphan")
    # Связь 1:N
    accounts = relationship("Account", back_populates="owner", cascade="all, delete-orphan")

class ClientProfile(Base):
    __tablename__ = "client_profiles"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), unique=True)
    phone = Column(String(20))
    address = Column(String(255))
    client = relationship("Client", back_populates="profile")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    account_number = Column(String(50))
    balance = Column(DECIMAL(15, 2), default=0.00)
    owner = relationship("Client", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(DECIMAL(15, 2))
    type = Column(String(10))
    account = relationship("Account", back_populates="transactions")
    
    # Связь N:M с категориями
    categories = relationship("Category", secondary="transaction_categories", back_populates="transactions")

# Связующая таблица для N:M
transaction_categories = Table(
    "transaction_categories", Base.metadata,
    Column("transaction_id", ForeignKey("transactions.id"), primary_key=True),
    Column("category_id", ForeignKey("categories.id"), primary_key=True)
)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    transactions = relationship("Transaction", secondary="transaction_categories", back_populates="categories")

# === CRUD операции ===
def main():
    Base.metadata.create_all(engine)
    db = Session()
    
    # === CREATE ===
    client = Client(username="ivanov", email="i@bank.com")
    db.add(client)
    db.commit()
    db.refresh(client)
    
    # 1:1 — Профиль
    profile = ClientProfile(client_id=client.id, phone="+79990000000", address="г. Москва")
    db.add(profile)
    db.commit()
    
    # 1:N — Счёт
    account = Account(client_id=client.id, account_number="40817810000000001234", balance=10000.00)
    db.add(account)
    db.commit()
    
    # 1:N — Транзакция
    transaction = Transaction(account_id=account.id, amount=500.00, type="debit")
    db.add(transaction)
    db.commit()
    
    # N:M — Категории
    cat1 = Category(name="Продукты")
    cat2 = Category(name="Транспорт")
    db.add_all([cat1, cat2])
    db.commit()
    
    transaction.categories.append(cat1)
    transaction.categories.append(cat2)
    db.commit()
    
    # === READ ===
    clients = db.scalars(select(Client).where(Client.email.like("%@bank.com"))).all()
    print(f"ORM filter: {[c.username for c in clients]}")
    
    # Проверка 1:1
    client_with_profile = db.query(Client).join(ClientProfile).first()
    print(f"1:1 relation: {client_with_profile.username} - {client_with_profile.profile.phone}")
    
    # Проверка N:M
    tx = db.query(Transaction).first()
    print(f"N:M relation: {[c.name for c in tx.categories]}")
    
    # === UPDATE ===
    account.balance += Decimal('5000.00')
    db.commit()
    
    # === RAW SQL (выполняем ДО удаления!) ===
    with engine.connect() as conn:
        conn.execute(Transaction.__table__.insert().values(
            account_id=account.id,  # ← теперь счёт ещё существует
            amount=100.00, 
            type="debit"
        ))
        conn.commit()
        count = conn.scalar(select(func.count()).select_from(Transaction.__table__))
        print(f"SQL count: {count}")
    
    # === DELETE (в самом конце) ===
    db.delete(client)  # каскадно удалит профиль, счета, транзакции
    db.commit()
    
    # === Transaction test ===
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