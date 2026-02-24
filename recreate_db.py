# Script simple para crear todas las tablas
from app import app, db

with app.app_context():
    print("Eliminando todas las tablas...")
    db.drop_all()
    print("✓ Tablas eliminadas")
    
    print("\nCreando todas las tablas...")
    db.create_all()
    print("✓ Tablas creadas")
    
    print("\n¡Base de datos lista!")
    print("Ahora ejecuta:")
    print("  1. python initData.py  (para cargar datos de prueba)")
    print("  2. python migrate_preventivo.py  (para migrar preventivos)")
