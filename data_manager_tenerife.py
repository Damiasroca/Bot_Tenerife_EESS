import pandas as pd
import mysql.connector as msql
from mysql.connector import Error
import secret
import datetime
from geopy.distance import geodesic
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import os
import json
import glob
from constants_tenerife import FUEL_TYPES, MUNICIPALITIES
from sqlalchemy import create_engine
import pytz
import logging

logger = logging.getLogger(__name__)

class TenerifeDataManager:
    def __init__(self):
        self.db_config = {
            'host': secret.secret['db_host'],
            'user': secret.secret['db_user'],
            'password': secret.secret['db_password'],
            'database': 'tenerife'  # New database for Tenerife
        }
        self.connection = None
        self.sqlalchemy_engine = None
        self.data = None
        self.last_update_time = None

    def connect(self):
        try:
            self.connection = msql.connect(**self.db_config)
            print("Connected to Tenerife MySQL database")
            
            # Also create SQLAlchemy engine for pandas (eliminates warning)
            connection_string = f"mysql+mysqlconnector://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}/{self.db_config['database']}"
            self.sqlalchemy_engine = create_engine(connection_string)
            
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise

    def create_database_and_tables(self):
        """Create the Tenerife database and all necessary tables."""
        try:
            # First connect without specifying database
            temp_config = self.db_config.copy()
            temp_config.pop('database')
            temp_conn = msql.connect(**temp_config)
            cursor = temp_conn.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS tenerife")
            print("Tenerife database created/verified")
            
            cursor.close()
            temp_conn.close()
            
            # Now connect to the tenerife database
            self.connect()
            cursor = self.connection.cursor()
            
            # Create main fuel stations table with all Tenerife fuel types
            stations_table = """
            CREATE TABLE IF NOT EXISTS estaciones_servicio (
                id INT AUTO_INCREMENT PRIMARY KEY,
                IDEESS VARCHAR(20) UNIQUE,
                cp VARCHAR(10),
                direccion TEXT,
                horario TEXT,
                latitud DECIMAL(10, 8),
                localidad VARCHAR(100),
                longitud_wgs84 DECIMAL(11, 8),
                margen VARCHAR(5),
                municipio VARCHAR(100),
                provincia VARCHAR(100),
                remision VARCHAR(10),
                rotulo VARCHAR(100),
                tipo_venta VARCHAR(5),
                bio_etanol VARCHAR(10),
                ester_metilico VARCHAR(10),
                id_municipio VARCHAR(10),
                id_provincia VARCHAR(10),
                id_ccaa VARCHAR(10),
                
                -- All fuel types from Tenerife data
                precio_adblue DECIMAL(5, 3),
                precio_amoniaco DECIMAL(5, 3),
                precio_biodiesel DECIMAL(5, 3),
                precio_bioetanol DECIMAL(5, 3),
                precio_biogas_natural_comprimido DECIMAL(5, 3),
                precio_biogas_natural_licuado DECIMAL(5, 3),
                precio_diesel_renovable DECIMAL(5, 3),
                precio_gas_natural_comprimido DECIMAL(5, 3),
                precio_gas_natural_licuado DECIMAL(5, 3),
                precio_gases_licuados_del_petroleo DECIMAL(5, 3),
                precio_gasoleo_a DECIMAL(5, 3),
                precio_gasoleo_b DECIMAL(5, 3),
                precio_gasoleo_premium DECIMAL(5, 3),
                precio_gasolina_95_e10 DECIMAL(5, 3),
                precio_gasolina_95_e25 DECIMAL(5, 3),
                precio_gasolina_95_e5 DECIMAL(5, 3),
                precio_gasolina_95_e5_premium DECIMAL(5, 3),
                precio_gasolina_95_e85 DECIMAL(5, 3),
                precio_gasolina_98_e10 DECIMAL(5, 3),
                precio_gasolina_98_e5 DECIMAL(5, 3),
                precio_gasolina_renovable DECIMAL(5, 3),
                precio_hidrogeno DECIMAL(5, 3),
                precio_metanol DECIMAL(5, 3),
                
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_municipio (municipio),
                INDEX idx_localidad (localidad),
                INDEX idx_rotulo (rotulo),
                INDEX idx_gasolina_95_e5 (precio_gasolina_95_e5),
                INDEX idx_gasoleo_a (precio_gasoleo_a),
                INDEX idx_ideess (IDEESS),
                INDEX idx_location (latitud, longitud_wgs84)
            )
            """
            
            # Create historical prices table for Tenerife
            historical_table = """
            CREATE TABLE IF NOT EXISTS historical_prices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE NOT NULL,
                ideess VARCHAR(20),
                rotulo VARCHAR(100),
                localidad VARCHAR(100),
                municipio VARCHAR(100),
                direccion TEXT,
                latitud DECIMAL(10, 8),
                longitud_wgs84 DECIMAL(11, 8),
                
                -- Key fuel prices for historical tracking
                precio_gasolina_95_e5 DECIMAL(5, 3),
                precio_gasoleo_a DECIMAL(5, 3),
                precio_gasolina_98_e5 DECIMAL(5, 3),
                precio_gasoleo_premium DECIMAL(5, 3),
                precio_gases_licuados_del_petroleo DECIMAL(5, 3),
                precio_gasoleo_b DECIMAL(5, 3),
                precio_adblue DECIMAL(5, 3),
                
                INDEX idx_date (date),
                INDEX idx_municipio (municipio),
                INDEX idx_ideess (ideess),
                INDEX idx_date_municipio (date, municipio)
            )
            """
            
            # Create user subscriptions table
            subscriptions_table = """
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username VARCHAR(255),
                fuel_type VARCHAR(50) NOT NULL,
                price_threshold DECIMAL(5, 3) NOT NULL,
                municipio VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                INDEX idx_user_id (user_id),
                INDEX idx_fuel_type (fuel_type),
                INDEX idx_active (is_active),
                INDEX idx_municipio (municipio)
            )
            """
            
            # Create users table for analytics
            users_table = """
            CREATE TABLE IF NOT EXISTS bot_users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                language_code VARCHAR(10),
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                interaction_count INT DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                INDEX idx_username (username),
                INDEX idx_last_seen (last_seen),
                INDEX idx_is_active (is_active)
            )
            """
            
            cursor.execute(stations_table)
            cursor.execute(historical_table)
            cursor.execute(subscriptions_table)
            cursor.execute(users_table)
            
            self.connection.commit()
            print("All Tenerife database tables created successfully")
            
        except Error as e:
            print(f"Error creating Tenerife database/tables: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def _convert_decimal(self, value):
        """Convert comma-decimal to dot-decimal for MySQL, handle empty strings."""
        if value is None or value == "" or pd.isna(value):
            return None
        try:
            # Convert to string and replace comma with dot
            str_val = str(value).replace(',', '.')
            if str_val.strip() == "":
                return None
            return float(str_val)
        except (ValueError, TypeError):
            return None

    def load_json_data(self):
        """Load all JSON files from municipis_original directory and process them."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        # Create tables if they don't exist
        self.create_database_and_tables()
        
        # Clear existing data for fresh load
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM estaciones_servicio")
        print("Cleared existing station data")
        
        # Get all JSON files from municipis_original directory
        json_files = glob.glob("municipis_original/*.json")
        
        if not json_files:
            print("No JSON files found in municipis_original directory")
            return
        
        total_stations = 0
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract municipality name from filename
                municipio_file = os.path.basename(json_file).replace('.json', '')
                print(f"Processing {municipio_file}...")
                
                if 'ListaEESSPrecio' not in data:
                    print(f"No fuel station data in {json_file}")
                    continue
                
                stations = data['ListaEESSPrecio']
                
                for station in stations:
                    try:
                        # Insert station data
                        insert_query = """
                        INSERT INTO estaciones_servicio (
                            IDEESS, cp, direccion, horario, latitud, localidad, longitud_wgs84,
                            margen, municipio, provincia, remision, rotulo, tipo_venta,
                            bio_etanol, ester_metilico, id_municipio, id_provincia, id_ccaa,
                            precio_adblue, precio_amoniaco, precio_biodiesel, precio_bioetanol,
                            precio_biogas_natural_comprimido, precio_biogas_natural_licuado,
                            precio_diesel_renovable, precio_gas_natural_comprimido,
                            precio_gas_natural_licuado, precio_gases_licuados_del_petroleo,
                            precio_gasoleo_a, precio_gasoleo_b, precio_gasoleo_premium,
                            precio_gasolina_95_e10, precio_gasolina_95_e25, precio_gasolina_95_e5,
                            precio_gasolina_95_e5_premium, precio_gasolina_95_e85,
                            precio_gasolina_98_e10, precio_gasolina_98_e5, precio_gasolina_renovable,
                            precio_hidrogeno, precio_metanol
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        ) ON DUPLICATE KEY UPDATE
                            cp = VALUES(cp), direccion = VALUES(direccion), horario = VALUES(horario),
                            latitud = VALUES(latitud), localidad = VALUES(localidad),
                            longitud_wgs84 = VALUES(longitud_wgs84), margen = VALUES(margen),
                            municipio = VALUES(municipio), provincia = VALUES(provincia),
                            remision = VALUES(remision), rotulo = VALUES(rotulo),
                            tipo_venta = VALUES(tipo_venta), bio_etanol = VALUES(bio_etanol),
                            ester_metilico = VALUES(ester_metilico), id_municipio = VALUES(id_municipio),
                            id_provincia = VALUES(id_provincia), id_ccaa = VALUES(id_ccaa),
                            precio_adblue = VALUES(precio_adblue), precio_amoniaco = VALUES(precio_amoniaco),
                            precio_biodiesel = VALUES(precio_biodiesel), precio_bioetanol = VALUES(precio_bioetanol),
                            precio_biogas_natural_comprimido = VALUES(precio_biogas_natural_comprimido),
                            precio_biogas_natural_licuado = VALUES(precio_biogas_natural_licuado),
                            precio_diesel_renovable = VALUES(precio_diesel_renovable),
                            precio_gas_natural_comprimido = VALUES(precio_gas_natural_comprimido),
                            precio_gas_natural_licuado = VALUES(precio_gas_natural_licuado),
                            precio_gases_licuados_del_petroleo = VALUES(precio_gases_licuados_del_petroleo),
                            precio_gasoleo_a = VALUES(precio_gasoleo_a), precio_gasoleo_b = VALUES(precio_gasoleo_b),
                            precio_gasoleo_premium = VALUES(precio_gasoleo_premium),
                            precio_gasolina_95_e10 = VALUES(precio_gasolina_95_e10),
                            precio_gasolina_95_e25 = VALUES(precio_gasolina_95_e25),
                            precio_gasolina_95_e5 = VALUES(precio_gasolina_95_e5),
                            precio_gasolina_95_e5_premium = VALUES(precio_gasolina_95_e5_premium),
                            precio_gasolina_95_e85 = VALUES(precio_gasolina_95_e85),
                            precio_gasolina_98_e10 = VALUES(precio_gasolina_98_e10),
                            precio_gasolina_98_e5 = VALUES(precio_gasolina_98_e5),
                            precio_gasolina_renovable = VALUES(precio_gasolina_renovable),
                            precio_hidrogeno = VALUES(precio_hidrogeno), precio_metanol = VALUES(precio_metanol)
                        """
                        
                        cursor.execute(insert_query, (
                            station.get('IDEESS'),
                            station.get('C.P.'),
                            station.get('Dirección'),
                            station.get('Horario'),
                            self._convert_decimal(station.get('Latitud')),
                            station.get('Localidad'),
                            self._convert_decimal(station.get('Longitud (WGS84)')),
                            station.get('Margen'),
                            station.get('Municipio'),
                            station.get('Provincia'),
                            station.get('Remisión'),
                            station.get('Rótulo'),
                            station.get('Tipo Venta'),
                            station.get('% BioEtanol'),
                            station.get('% Éster metílico'),
                            station.get('IDMunicipio'),
                            station.get('IDProvincia'),
                            station.get('IDCCAA'),
                            
                            # All fuel prices
                            self._convert_decimal(station.get('Precio Adblue')),
                            self._convert_decimal(station.get('Precio Amoniaco')),
                            self._convert_decimal(station.get('Precio Biodiesel')),
                            self._convert_decimal(station.get('Precio Bioetanol')),
                            self._convert_decimal(station.get('Precio Biogas Natural Comprimido')),
                            self._convert_decimal(station.get('Precio Biogas Natural Licuado')),
                            self._convert_decimal(station.get('Precio Diésel Renovable')),
                            self._convert_decimal(station.get('Precio Gas Natural Comprimido')),
                            self._convert_decimal(station.get('Precio Gas Natural Licuado')),
                            self._convert_decimal(station.get('Precio Gases licuados del petróleo')),
                            self._convert_decimal(station.get('Precio Gasoleo A')),
                            self._convert_decimal(station.get('Precio Gasoleo B')),
                            self._convert_decimal(station.get('Precio Gasoleo Premium')),
                            self._convert_decimal(station.get('Precio Gasolina 95 E10')),
                            self._convert_decimal(station.get('Precio Gasolina 95 E25')),
                            self._convert_decimal(station.get('Precio Gasolina 95 E5')),
                            self._convert_decimal(station.get('Precio Gasolina 95 E5 Premium')),
                            self._convert_decimal(station.get('Precio Gasolina 95 E85')),
                            self._convert_decimal(station.get('Precio Gasolina 98 E10')),
                            self._convert_decimal(station.get('Precio Gasolina 98 E5')),
                            self._convert_decimal(station.get('Precio Gasolina Renovable')),
                            self._convert_decimal(station.get('Precio Hidrogeno')),
                            self._convert_decimal(station.get('Precio Metanol'))
                        ))
                        
                        total_stations += 1
                        
                    except Error as e:
                        print(f"Error inserting station {station.get('IDEESS', 'unknown')}: {e}")
                        continue
                
            except Exception as e:
                print(f"Error processing file {json_file}: {e}")
                continue
        
        self.connection.commit()
        cursor.close()
        
        print(f"✅ Loaded {total_stations} stations from {len(json_files)} municipalities")
        
        # Store timestamp
        self.last_update_time = datetime.datetime.now()
        self._save_update_timestamp()
        
        # Store daily snapshot for historical data
        self.store_daily_snapshot()

    def _save_update_timestamp(self):
        """Save the update timestamp to file."""
        try:
            timestamp_str = self.last_update_time.strftime("%d/%m/%Y %H:%M:%S")
            with open('last_api_fetch_tenerife.txt', 'w') as f:
                f.write(timestamp_str)
        except Exception as e:
            print(f"Error saving timestamp: {e}")

    def load_data_from_db(self):
        """Load current station data from database into pandas DataFrame."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        query = "SELECT * FROM estaciones_servicio"
        try:
            # Use SQLAlchemy engine to eliminate pandas warning
            self.data = pd.read_sql(query, self.sqlalchemy_engine)
            print(f"Loaded {len(self.data)} stations from database")
            
            # Load timestamp
            self._load_update_timestamp()
            
            # Store daily snapshot for historical data
            self.store_daily_snapshot()
            
        except Exception as e:
            print(f"Error loading data from database: {e}")
            raise

    def _load_update_timestamp(self):
        """Load the update timestamp from file."""
        try:
            with open('last_api_fetch_tenerife.txt', 'r') as f:
                timestamp_str = f.read().strip()
                self.last_update_time = datetime.datetime.strptime(timestamp_str, "%d/%m/%Y %H:%M:%S")
        except FileNotFoundError:
            self.last_update_time = datetime.datetime.now()
        except Exception as e:
            print(f"Error loading timestamp: {e}")
            self.last_update_time = datetime.datetime.now()

    def store_daily_snapshot(self):
        """Store a daily snapshot of current prices for historical tracking."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        today = datetime.date.today()
        
        # Check if we already have data for today
        check_query = "SELECT COUNT(*) FROM historical_prices WHERE date = %s"
        cursor.execute(check_query, (today,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"Historical data for {today} already exists")
            cursor.close()
            # Still check for alerts even if historical data exists
            self._check_and_send_alerts()
            return
        
        # Insert today's data for key fuel types
        insert_query = """
        INSERT INTO historical_prices 
        (date, ideess, rotulo, localidad, municipio, direccion, latitud, longitud_wgs84,
         precio_gasolina_95_e5, precio_gasoleo_a, precio_gasolina_98_e5, 
         precio_gasoleo_premium, precio_gases_licuados_del_petroleo, 
         precio_gasoleo_b, precio_adblue)
        SELECT %s, IDEESS, rotulo, localidad, municipio, direccion, latitud, longitud_wgs84,
               precio_gasolina_95_e5, precio_gasoleo_a, precio_gasolina_98_e5,
               precio_gasoleo_premium, precio_gases_licuados_del_petroleo,
               precio_gasoleo_b, precio_adblue
        FROM estaciones_servicio
        WHERE precio_gasolina_95_e5 IS NOT NULL OR precio_gasoleo_a IS NOT NULL
        """
        
        try:
            cursor.execute(insert_query, (today,))
            self.connection.commit()
            print(f"Daily snapshot stored for {today}")
            
            # After storing new data, check for price alerts
            self._check_and_send_alerts()
            
        except Error as e:
            print(f"Error storing daily snapshot: {e}")
            self.connection.rollback()
        finally:
            cursor.close()

    def _check_and_send_alerts(self):
        """Check for price alerts and trigger notifications (internal helper)."""
        try:
            notifications = self.check_price_alerts()
            if notifications:
                print(f"🔔 Found {len(notifications)} price alerts to send")
                # You can implement actual sending here or use the notification_sender.py
                # For now, just log that alerts were found
                for notification in notifications:
                    print(f"   Alert: {notification['fuel_type']} at {notification['current_price']}€ for user {notification['user_id']}")
            else:
                print("✅ No price alerts triggered")
        except Exception as e:
            print(f"Error checking alerts: {e}")

    def get_stations_by_fuel_ascending(self, fuel_type, limit=None):
        """Get stations ordered by fuel price (ascending) with pagination support."""
        if self.data is None:
            self.load_data_from_db()
        
        if fuel_type not in FUEL_TYPES:
            return pd.DataFrame()
        
        fuel_config = FUEL_TYPES[fuel_type]
        column_name = fuel_config['column'].lower()
        
        # Filter out stations without this fuel type and sort by price
        filtered_data = self.data[self.data[column_name].notna() & (self.data[column_name] > 0)]
        sorted_data = filtered_data.sort_values(by=column_name, ascending=True)
        
        if limit:
            return sorted_data.head(limit)
        
        return sorted_data

    def get_stations_by_fuel_descending(self, fuel_type, limit=None):
        """Get stations ordered by fuel price (descending) with pagination support."""
        if self.data is None:
            self.load_data_from_db()
        
        if fuel_type not in FUEL_TYPES:
            return pd.DataFrame()
        
        fuel_config = FUEL_TYPES[fuel_type]
        column_name = fuel_config['column'].lower()
        
        # Filter out stations without this fuel type and sort by price
        filtered_data = self.data[self.data[column_name].notna() & (self.data[column_name] > 0)]
        sorted_data = filtered_data.sort_values(by=column_name, ascending=False)
        
        if limit:
            return sorted_data.head(limit)
        
        return sorted_data

    def get_stations_by_municipality(self, municipality_key, offset=0, limit=5):
        """Get stations for a specific municipality with pagination using IDMunicipio."""
        if self.data is None:
            self.load_data_from_db()
        
        if municipality_key not in MUNICIPALITIES:
            return pd.DataFrame(), 0
        
        municipality_id = MUNICIPALITIES[municipality_key]['id']
        
        # Filter by municipality ID - much more reliable than name matching
        filtered_data = self.data[
            self.data['id_municipio'].astype(str) == municipality_id
        ]
        
        total_stations = len(filtered_data)
        
        # Apply pagination
        paginated_data = filtered_data.iloc[offset:offset + limit]
        
        return paginated_data, total_stations

    def search_municipalities(self, search_term):
        """Search municipalities by name."""
        matches = []
        search_lower = search_term.lower()
        
        for key, muni_info in MUNICIPALITIES.items():
            if search_lower in muni_info['display'].lower():
                matches.append((key, muni_info['display']))
        
        return matches

    def get_available_fuel_types(self):
        """Get list of available fuel types ordered by priority."""
        if self.data is None:
            self.load_data_from_db()
        
        available_fuels = []
        
        for fuel_key, fuel_info in sorted(FUEL_TYPES.items(), key=lambda x: x[1]['priority']):
            column_name = fuel_info['column'].lower()
            
            # Check if this fuel type has any data
            if column_name in self.data.columns:
                stations_with_fuel = self.data[
                    self.data[column_name].notna() & (self.data[column_name] > 0)
                ]
                
                if len(stations_with_fuel) > 0:
                    available_fuels.append({
                        'key': fuel_key,
                        'display': fuel_info['display'],
                        'button': fuel_info['button'],
                        'stations_count': len(stations_with_fuel),
                        'priority': fuel_info['priority']
                    })
        
        return available_fuels

    def find_stations_near_location(self, user_lat, user_lon, radius_km=10):
        """Find gas stations within radius, sorted by price and then distance."""
        if self.data is None:
            self.load_data_from_db()
        
        stations_in_radius = []
        user_location = (user_lat, user_lon)
        
        for _, station in self.data.iterrows():
            if pd.isna(station['latitud']) or pd.isna(station['longitud_wgs84']):
                continue
            
            try:
                station_location = (float(station['latitud']), float(station['longitud_wgs84']))
                distance = geodesic(user_location, station_location).kilometers
                
                if distance <= radius_km:
                    station_data = station.to_dict()
                    station_data['distance'] = round(distance, 2)
                    stations_in_radius.append(station_data)
            except (ValueError, TypeError):
                continue
        
        # Sort by price (Gasolina 95 E5) ascending, then by distance ascending.
        # Stations without a price are pushed to the end of the list.
        stations_in_radius.sort(key=lambda x: (
            x.get('precio_gasolina_95_e5') is None, 
            x.get('precio_gasolina_95_e5', float('inf')), 
            x.get('distance')
        ))
        
        return stations_in_radius

    def get_last_update_time(self):
        """Get the last update time, adjusted for Canary Islands timezone."""
        try:
            with open('last_api_fetch_tenerife.txt', 'r') as f:
                timestamp_str = f.read().strip()
            
            # The timestamp is saved in the server's timezone (CET/CEST).
            # We need to convert it to the Canary Islands timezone.
            
            # Define timezones
            server_tz = pytz.timezone('Europe/Madrid')
            canary_tz = pytz.timezone('Atlantic/Canary')
            
            # Create a naive datetime object from the string
            naive_dt = datetime.datetime.strptime(timestamp_str, "%d/%m/%Y %H:%M:%S")
            
            # Localize it to the server's timezone
            server_dt = server_tz.localize(naive_dt)
            
            # Convert it to the Canary Islands timezone
            canary_dt = server_dt.astimezone(canary_tz)
            
            # Format it for display
            return canary_dt.strftime("%d/%m/%Y %H:%M:%S %Z")

        except FileNotFoundError:
            return "No disponible"
        except Exception as e:
            logger.error(f"Error reading or converting timestamp: {e}")
            return "No disponible"

    def track_user_interaction(self, user_id, username=None, first_name=None, last_name=None, language_code=None):
        """Track user interactions for analytics."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        
        try:
            # Insert or update user information
            query = """
            INSERT INTO bot_users (user_id, username, first_name, last_name, language_code, interaction_count)
            VALUES (%s, %s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                username = VALUES(username),
                first_name = VALUES(first_name),
                last_name = VALUES(last_name),
                language_code = VALUES(language_code),
                interaction_count = interaction_count + 1,
                last_seen = CURRENT_TIMESTAMP
            """
            
            cursor.execute(query, (user_id, username, first_name, last_name, language_code))
            self.connection.commit()
            
        except Error as e:
            print(f"Error tracking user interaction: {e}")
        finally:
            cursor.close()

    def generate_price_chart(self, fuel_type, days=7):
        """Generate price evolution chart for a fuel type."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        if fuel_type not in FUEL_TYPES:
            return None
        
        fuel_config = FUEL_TYPES[fuel_type]
        fuel_column = fuel_config['column'].lower()
        fuel_display = fuel_config['display']
        
        # Calculate date range
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Query historical data
        query = f"""
        SELECT date, AVG({fuel_column}) as avg_price, MIN({fuel_column}) as min_price, MAX({fuel_column}) as max_price
        FROM historical_prices 
        WHERE date >= %s AND date <= %s 
        AND {fuel_column} IS NOT NULL AND {fuel_column} > 0
        GROUP BY date
        ORDER BY date
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (start_date, end_date))
            data = cursor.fetchall()
            cursor.close()
            
            if not data or len(data) < 2:
                return None  # Not enough data
            
            # Prepare data for plotting
            dates = [row[0] for row in data]
            avg_prices = [float(row[1]) for row in data]
            min_prices = [float(row[2]) for row in data]
            max_prices = [float(row[3]) for row in data]
            
            # Create matplotlib figure
            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Plot data
            ax.plot(dates, avg_prices, 'b-', linewidth=2, label='Precio promedio', marker='o')
            ax.fill_between(dates, min_prices, max_prices, alpha=0.3, color='blue', label='Rango de precios')
            
            # Customize chart
            ax.set_title(f'Evolución de precios - {fuel_display}\n({days} días)', fontsize=16, fontweight='bold')
            ax.set_xlabel('Fecha', fontsize=12)
            ax.set_ylabel('Precio (€)', fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Format dates on x-axis
            if days <= 7:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
            
            # Rotate date labels
            plt.xticks(rotation=45)
            
            # Add statistics text
            current_avg = avg_prices[-1]
            min_price_overall = min(min_prices)
            max_price_overall = max(max_prices)
            
            stats_text = f'Actual: {current_avg:.3f}€\nMín: {min_price_overall:.3f}€\nMáx: {max_price_overall:.3f}€'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # Tight layout and save
            plt.tight_layout()
            
            # Create charts directory if it doesn't exist
            os.makedirs('charts', exist_ok=True)
            
            # Generate unique filename
            chart_filename = f'charts/chart_{fuel_type}_{days}d_{int(datetime.datetime.now().timestamp())}.png'
            plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_filename
            
        except Error as e:
            print(f"Error generating chart: {e}")
            return None

    def create_historical_backfill(self, days_back=30):
        """Create historical data for testing charts (simulates past data)."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        
        # Get current station data
        cursor.execute("SELECT COUNT(*) FROM estaciones_servicio WHERE precio_gasolina_95_e5 IS NOT NULL")
        station_count = cursor.fetchone()[0]
        
        if station_count == 0:
            print("No station data available for backfill")
            cursor.close()
            return
        
        print(f"Creating {days_back} days of historical data...")
        
        # Create data for each day going backwards
        for i in range(days_back, 0, -1):
            target_date = datetime.date.today() - datetime.timedelta(days=i)
            
            # Check if data already exists for this date
            cursor.execute("SELECT COUNT(*) FROM historical_prices WHERE date = %s", (target_date,))
            if cursor.fetchone()[0] > 0:
                print(f"Data for {target_date} already exists, skipping...")
                continue
            
            # Create price variations (simulate market fluctuations)
            import random
            price_multiplier = 1.0 + random.uniform(-0.05, 0.05)  # ±5% variation
            
            # Insert historical data with slight price variations
            insert_query = f"""
            INSERT INTO historical_prices 
            (date, ideess, rotulo, localidad, municipio, direccion, latitud, longitud_wgs84,
             precio_gasolina_95_e5, precio_gasoleo_a, precio_gasolina_98_e5, 
             precio_gasoleo_premium, precio_gases_licuados_del_petroleo, 
             precio_gasoleo_b, precio_adblue)
            SELECT 
                %s, 
                IDEESS, rotulo, localidad, municipio, direccion, latitud, longitud_wgs84,
                CASE WHEN precio_gasolina_95_e5 IS NOT NULL THEN ROUND(precio_gasolina_95_e5 * %s, 3) END,
                CASE WHEN precio_gasoleo_a IS NOT NULL THEN ROUND(precio_gasoleo_a * %s, 3) END,
                CASE WHEN precio_gasolina_98_e5 IS NOT NULL THEN ROUND(precio_gasolina_98_e5 * %s, 3) END,
                CASE WHEN precio_gasoleo_premium IS NOT NULL THEN ROUND(precio_gasoleo_premium * %s, 3) END,
                CASE WHEN precio_gases_licuados_del_petroleo IS NOT NULL THEN ROUND(precio_gases_licuados_del_petroleo * %s, 3) END,
                CASE WHEN precio_gasoleo_b IS NOT NULL THEN ROUND(precio_gasoleo_b * %s, 3) END,
                CASE WHEN precio_adblue IS NOT NULL THEN ROUND(precio_adblue * %s, 3) END
            FROM estaciones_servicio
            WHERE precio_gasolina_95_e5 IS NOT NULL OR precio_gasoleo_a IS NOT NULL
            """
            
            try:
                cursor.execute(insert_query, (
                    target_date, 
                    price_multiplier, price_multiplier, price_multiplier, price_multiplier,
                    price_multiplier, price_multiplier, price_multiplier
                ))
                self.connection.commit()
                print(f"✅ Created historical data for {target_date} (variation: {price_multiplier:.3f})")
                
            except Error as e:
                print(f"❌ Error creating data for {target_date}: {e}")
                self.connection.rollback()
        
        cursor.close()
        print(f"🎯 Historical backfill completed! Charts should now work.")

    def check_historical_data_status(self):
        """Check the status of historical data for debugging."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        
        # Check main table
        cursor.execute("SELECT COUNT(*) FROM estaciones_servicio")
        station_count = cursor.fetchone()[0]
        
        # Check historical table
        cursor.execute("SELECT COUNT(*) FROM historical_prices")
        historical_count = cursor.fetchone()[0]
        
        # Check date range
        cursor.execute("SELECT MIN(date), MAX(date) FROM historical_prices")
        date_range = cursor.fetchone()
        
        # Check data by date
        cursor.execute("SELECT date, COUNT(*) FROM historical_prices GROUP BY date ORDER BY date DESC LIMIT 10")
        recent_data = cursor.fetchall()
        
        cursor.close()
        
        print("📊 **Historical Data Status:**")
        print(f"Main stations: {station_count}")
        print(f"Historical records: {historical_count}")
        print(f"Date range: {date_range[0]} to {date_range[1]}" if date_range[0] else "No historical data")
        print("\n📅 **Recent historical data:**")
        for date, count in recent_data:
            print(f"  {date}: {count} records")
        
        if historical_count < 2:
            print("\n⚠️ **Charts won't work** - need at least 2 days of data")
            print("💡 Run: tenerife_data_manager.create_historical_backfill() to fix this")
        else:
            print(f"\n✅ **Charts should work** - {historical_count} historical records available")
        
        return {
            'station_count': station_count,
            'historical_count': historical_count,
            'date_range': date_range,
            'recent_data': recent_data
        }

    # Admin Analytics Functions
    def get_admin_statistics(self):
        """Get comprehensive bot statistics for admin dashboard."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        stats = {}
        
        try:
            # User statistics
            cursor.execute("SELECT COUNT(*) FROM bot_users")
            stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bot_users WHERE last_seen >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
            stats['active_users_7d'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bot_users WHERE last_seen >= DATE_SUB(NOW(), INTERVAL 30 DAY)")
            stats['active_users_30d'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bot_users WHERE DATE(first_seen) = CURDATE()")
            stats['new_users_today'] = cursor.fetchone()[0]
            
            # Interaction statistics
            cursor.execute("SELECT SUM(interaction_count) FROM bot_users")
            stats['total_interactions'] = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COUNT(*) FROM bot_users 
                WHERE last_seen >= CURDATE() AND last_seen < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
            """)
            stats['interactions_today'] = cursor.fetchone()[0]
            
            if stats['total_users'] > 0:
                stats['avg_interactions'] = stats['total_interactions'] / stats['total_users']
            else:
                stats['avg_interactions'] = 0
            
            # Database statistics
            cursor.execute("SELECT COUNT(*) FROM estaciones_servicio")
            stats['station_count'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM historical_prices")
            stats['historical_count'] = cursor.fetchone()[0]
            
            # Last update time
            stats['last_update'] = self.get_last_update_time()
            
            # Top municipalities by station count
            cursor.execute("""
                SELECT municipio, COUNT(*) as count 
                FROM estaciones_servicio 
                GROUP BY municipio 
                ORDER BY count DESC 
                LIMIT 10
            """)
            stats['top_municipalities'] = cursor.fetchall()
            
        except Error as e:
            print(f"Error getting admin statistics: {e}")
            stats = {'error': str(e)}
        finally:
            cursor.close()
        
        return stats

    def get_recent_users(self, limit=20):
        """Get recent users with their activity data."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            query = """
            SELECT user_id, username, first_name, last_name, language_code,
                   interaction_count, first_seen, last_seen, is_active
            FROM bot_users 
            ORDER BY last_seen DESC 
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            users = cursor.fetchall()
            
        except Error as e:
            print(f"Error getting recent users: {e}")
            users = []
        finally:
            cursor.close()
        
        return users

    def get_user_details(self, user_id):
        """Get detailed information about a specific user."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            query = """
            SELECT user_id, username, first_name, last_name, language_code,
                   interaction_count, first_seen, last_seen, is_active
            FROM bot_users 
            WHERE user_id = %s
            """
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()
            
        except Error as e:
            print(f"Error getting user details: {e}")
            user = None
        finally:
            cursor.close()
        
        return user

    def get_all_active_users(self):
        """Get all active users for broadcasting."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            query = """
            SELECT user_id, first_name, username
            FROM bot_users 
            WHERE is_active = TRUE
            ORDER BY last_seen DESC
            """
            cursor.execute(query)
            users = cursor.fetchall()
            
        except Error as e:
            print(f"Error getting active users: {e}")
            users = []
        finally:
            cursor.close()
        
        return users

    def get_user_activity_stats(self, days=30):
        """Get user activity statistics for the last N days."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        
        try:
            # Daily new users
            query = """
            SELECT DATE(first_seen) as date, COUNT(*) as new_users
            FROM bot_users 
            WHERE first_seen >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(first_seen)
            ORDER BY date DESC
            """
            cursor.execute(query, (days,))
            daily_new_users = cursor.fetchall()
            
            # Daily active users  
            query = """
            SELECT DATE(last_seen) as date, COUNT(*) as active_users
            FROM bot_users 
            WHERE last_seen >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(last_seen)
            ORDER BY date DESC
            """
            cursor.execute(query, (days,))
            daily_active_users = cursor.fetchall()
            
            return {
                'daily_new_users': daily_new_users,
                'daily_active_users': daily_active_users
            }
            
        except Error as e:
            print(f"Error getting activity stats: {e}")
            return {'error': str(e)}
        finally:
            cursor.close()

    def get_popular_features(self):
        """Get statistics about which features are most used (would need tracking)."""
        # This would require implementing feature tracking in the bot
        # For now, return basic data we have
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        
        try:
            # Most popular fuel types (from available data)
            available_fuels = self.get_available_fuel_types()
            fuel_popularity = [(fuel['display'], fuel['stations_count']) for fuel in available_fuels]
            
            # Most popular municipalities (by station count)
            cursor.execute("""
                SELECT municipio, COUNT(*) as station_count
                FROM estaciones_servicio 
                GROUP BY municipio 
                ORDER BY station_count DESC 
                LIMIT 10
            """)
            popular_municipalities = cursor.fetchall()
            
            return {
                'fuel_popularity': fuel_popularity,
                'popular_municipalities': popular_municipalities
            }
            
        except Error as e:
            print(f"Error getting feature popularity: {e}")
            return {'error': str(e)}
        finally:
            cursor.close()

    # Alert Management Functions
    def create_price_alert(self, user_id, username, fuel_type, price_threshold, municipality):
        """Create a new price alert for a user."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        
        try:
            # Check if user already has an alert for this fuel type and municipality
            check_query = """
            SELECT id FROM user_subscriptions 
            WHERE user_id = %s AND fuel_type = %s AND municipio = %s AND is_active = TRUE
            """
            cursor.execute(check_query, (user_id, fuel_type, municipality))
            existing_alert = cursor.fetchone()
            
            if existing_alert:
                # Update existing alert
                update_query = """
                UPDATE user_subscriptions 
                SET price_threshold = %s, created_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """
                cursor.execute(update_query, (price_threshold, existing_alert[0]))
                self.connection.commit()
                return True, "updated"
            else:
                # Create new alert
                insert_query = """
                INSERT INTO user_subscriptions 
                (user_id, username, fuel_type, price_threshold, municipio, is_active)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                """
                cursor.execute(insert_query, (user_id, username, fuel_type, price_threshold, municipality))
                self.connection.commit()
                return True, "created"
                
        except Error as e:
            print(f"Error creating price alert: {e}")
            self.connection.rollback()
            return False, str(e)
        finally:
            cursor.close()

    def get_user_alerts(self, user_id):
        """Get all active alerts for a user."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            query = """
            SELECT id, fuel_type, price_threshold, municipio, created_at
            FROM user_subscriptions 
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
            """
            cursor.execute(query, (user_id,))
            alerts = cursor.fetchall()
            return alerts
            
        except Error as e:
            print(f"Error getting user alerts: {e}")
            return []
        finally:
            cursor.close()

    def delete_alert(self, user_id, alert_id):
        """Delete a specific alert for a user."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        
        try:
            # Verify the alert belongs to the user before deleting
            delete_query = """
            UPDATE user_subscriptions 
            SET is_active = FALSE 
            WHERE id = %s AND user_id = %s AND is_active = TRUE
            """
            cursor.execute(delete_query, (alert_id, user_id))
            
            if cursor.rowcount > 0:
                self.connection.commit()
                return True
            else:
                return False
                
        except Error as e:
            print(f"Error deleting alert: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def check_price_alerts(self):
        """Check all active alerts and return notifications to send."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor(dictionary=True)
        notifications = []
        
        try:
            # Get all active alerts
            alerts_query = """
            SELECT s.id, s.user_id, s.username, s.fuel_type, s.price_threshold, s.municipio
            FROM user_subscriptions s
            WHERE s.is_active = TRUE
            """
            cursor.execute(alerts_query)
            alerts = cursor.fetchall()
            
            for alert in alerts:
                # Get current minimum price for this fuel type in this municipality
                fuel_column = None
                for fuel_key, fuel_info in FUEL_TYPES.items():
                    if fuel_key == alert['fuel_type']:
                        fuel_column = fuel_info['column'].lower()
                        break
                
                if not fuel_column:
                    continue
                
                # Get municipality ID
                municipality_id = None
                for muni_key, muni_info in MUNICIPALITIES.items():
                    if muni_info['display'] == alert['municipio']:
                        municipality_id = muni_info['id']
                        break
                
                if not municipality_id:
                    continue
                
                # Find cheapest station for this fuel in this municipality
                price_query = f"""
                SELECT MIN({fuel_column}) as min_price, rotulo, direccion
                FROM estaciones_servicio 
                WHERE id_municipio = %s AND {fuel_column} IS NOT NULL AND {fuel_column} > 0
                GROUP BY rotulo, direccion
                ORDER BY min_price ASC
                LIMIT 1
                """
                
                cursor.execute(price_query, (municipality_id,))
                result = cursor.fetchone()
                
                if result and result['min_price'] <= alert['price_threshold']:
                    notifications.append({
                        'user_id': alert['user_id'],
                        'alert_id': alert['id'],
                        'fuel_type': alert['fuel_type'],
                        'current_price': result['min_price'],
                        'threshold': alert['price_threshold'],
                        'municipality': alert['municipio'],
                        'station_name': result['rotulo'],
                        'station_address': result['direccion']
                    })
            
            return notifications
            
        except Error as e:
            print(f"Error checking price alerts: {e}")
            return []
        finally:
            cursor.close()

    def get_alert_statistics(self):
        """Get statistics about price alerts for admin dashboard."""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        
        try:
            # Total active alerts
            cursor.execute("SELECT COUNT(*) FROM user_subscriptions WHERE is_active = TRUE")
            total_alerts = cursor.fetchone()[0]
            
            # Alerts by fuel type
            cursor.execute("""
                SELECT fuel_type, COUNT(*) as count
                FROM user_subscriptions 
                WHERE is_active = TRUE
                GROUP BY fuel_type
                ORDER BY count DESC
            """)
            alerts_by_fuel = cursor.fetchall()
            
            # Alerts by municipality
            cursor.execute("""
                SELECT municipio, COUNT(*) as count
                FROM user_subscriptions 
                WHERE is_active = TRUE
                GROUP BY municipio
                ORDER BY count DESC
                LIMIT 10
            """)
            alerts_by_municipality = cursor.fetchall()
            
            return {
                'total_alerts': total_alerts,
                'alerts_by_fuel': alerts_by_fuel,
                'alerts_by_municipality': alerts_by_municipality
            }
            
        except Error as e:
            print(f"Error getting alert statistics: {e}")
            return {'error': str(e)}
        finally:
            cursor.close()

# Create global instance
tenerife_data_manager = TenerifeDataManager()

if __name__ == "__main__":
    print("Executing Tenerife Data Manager...")
    # This allows the script to be run directly to update the database
    # from the downloaded JSON files.
    
    # Create an instance of the manager
    manager = TenerifeDataManager()
    
    # Load the new data from JSON files into the database
    manager.load_json_data()
    
    # Store a snapshot of today's prices for historical analysis
    manager.store_daily_snapshot()
    
    print("Tenerife Data Manager execution finished.") 