import csv
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import Empresa, Planta, Zona, Linea, Maquina

def import_activos(csv_file):
    with open(csv_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                # 1. Empresa
                empresa = Empresa.query.filter_by(codigo=row['Empresa_Codigo']).first()
                if not empresa:
                    print(f"Creando Empresa: {row['Empresa_Nombre']}")
                    empresa = Empresa(
                        codigo=row['Empresa_Codigo'],
                        nombre=row['Empresa_Nombre']
                    )
                    db.session.add(empresa)
                    db.session.flush() # Para obtener el ID
                
                # 2. Planta
                planta = Planta.query.filter_by(codigo=row['Planta_Codigo'], empresaId=empresa.id).first()
                if not planta:
                    print(f"Creando Planta: {row['Planta_Nombre']}")
                    planta = Planta(
                        empresaId=empresa.id,
                        codigo=row['Planta_Codigo'],
                        nombre=row['Planta_Nombre']
                    )
                    db.session.add(planta)
                    db.session.flush()
                
                # 3. Zona
                zona = Zona.query.filter_by(codigo=row['Zona_Codigo'], plantaId=planta.id).first()
                if not zona:
                    print(f"Creando Zona: {row['Zona_Nombre']}")
                    zona = Zona(
                        plantaId=planta.id,
                        codigo=row['Zona_Codigo'],
                        nombre=row['Zona_Nombre']
                    )
                    db.session.add(zona)
                    db.session.flush()

                # 4. Linea
                linea = Linea.query.filter_by(codigo=row['Linea_Codigo'], zonaId=zona.id).first()
                if not linea:
                    print(f"Creando Línea: {row['Linea_Nombre']}")
                    linea = Linea(
                        zonaId=zona.id,
                        codigo=row['Linea_Codigo'],
                        nombre=row['Linea_Nombre']
                    )
                    db.session.add(linea)
                    db.session.flush()
                
                # 5. Maquina
                maquina = Maquina.query.filter_by(codigo=row['Maquina_Codigo'], lineaId=linea.id).first()
                if not maquina:
                    print(f"Creando Máquina: {row['Maquina_Nombre']}")
                    maquina = Maquina(
                        lineaId=linea.id,
                        codigo=row['Maquina_Codigo'],
                        nombre=row['Maquina_Nombre'],
                        modelo=row.get('Maquina_Modelo'),
                        fabricante=row.get('Maquina_Fabricante'),
                        numeroSerie=row.get('Maquina_NumSerie'),
                        descripcion=row.get('Maquina_Descripcion'),
                        criticidad=row.get('Maquina_Criticidad', 'media'),
                        estado=row.get('Maquina_Estado', 'operativo')
                    )
                    
                    if row.get('Maquina_FechaInstalacion'):
                        try:
                            maquina.fechaInstalacion = datetime.strptime(row['Maquina_FechaInstalacion'], '%Y-%m-%d').date()
                        except ValueError:
                            print(f"Advertencia: Formato de fecha incorrecto para {row['Maquina_Codigo']}")
                    
                    db.session.add(maquina)
                else:
                    print(f"Actualizando Máquina: {row['Maquina_Nombre']}")
                    maquina.nombre = row['Maquina_Nombre']
                    maquina.modelo = row.get('Maquina_Modelo')
                    maquina.fabricante = row.get('Maquina_Fabricante')
                    maquina.numeroSerie = row.get('Maquina_NumSerie')
                    maquina.descripcion = row.get('Maquina_Descripcion')
                    maquina.criticidad = row.get('Maquina_Criticidad', 'media')
                    maquina.estado = row.get('Maquina_Estado', 'operativo')
                    
                    if row.get('Maquina_FechaInstalacion'):
                        try:
                            maquina.fechaInstalacion = datetime.strptime(row['Maquina_FechaInstalacion'], '%Y-%m-%d').date()
                        except ValueError:
                            print(f"Advertencia: Formato de fecha incorrecto para {row['Maquina_Codigo']}")

            except Exception as e:
                print(f"Error procesando fila {row}: {e}")
                db.session.rollback()
                continue

        db.session.commit()
        print("Importación completada.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_activos.py <archivo_csv>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    with app.app_context():
        import_activos(csv_file)
