# test_connexion.py
from erpnext import ERPNextClient

client = ERPNextClient()

print("\n── TEST 1 : Stock faible ──")
stock = client.get_low_stock()
print(f"Résultat : {len(stock)} articles")
if stock:
    print("Premier article :", stock[0])

print("\n── TEST 2 : Commandes d'achat ──")
purchases = client.get_purchase_orders()
print(f"Résultat : {len(purchases)} commandes")
if purchases:
    print("Première commande :", purchases[0])

print("\n── TEST 3 : Ventes ──")
sales = client.get_sales_orders()
print(f"Résultat : {len(sales)} ventes")

print("\n── TEST 4 : Top articles ──")
top = client.get_top_items()
print(f"Résultat : {len(top)} articles")

print("\n── TEST 5 : Fournisseurs ──")
suppliers = client.get_suppliers()
print(f"Résultat : {len(suppliers)} fournisseurs")

print("\n── TEST 6 : Factures impayées ──")
invoices = client.get_unpaid_invoices()
print(f"Résultat : {len(invoices)} factures")

print("\n✅ Tests terminés !")