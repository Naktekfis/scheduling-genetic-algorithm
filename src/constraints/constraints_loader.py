import pandas as pd

class ConstraintLoader:
    def __init__(self, csv_path):
        """
        Memuat dan mengelola status constraint dari file CSV.
        """
        self.constraints = {}
        try:
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                constraint_id = str(row['ConstraintID']).strip()
                is_enabled_flag = (row['Enabled'] == 1 or str(row['Enabled']).strip() == '1')

                self.constraints[constraint_id] = {
                    'type': str(row['Type']).strip(),
                    'description': str(row['Description']).strip(),
                    'enabled': is_enabled_flag
                }
        except FileNotFoundError:
            print(f"Peringatan: File constraint '{csv_path}' tidak ditemukan. Semua constraint akan dianggap non-aktif.")
        except Exception as e:
            print(f"Error saat memuat constraint: {e}. Semua constraint akan dianggap non-aktif.")


    def is_enabled(self, constraint_id):
        """
        Memeriksa apakah sebuah constraint dengan ID tertentu aktif.
        Aman digunakan bahkan jika ID tidak ada.
        """
        return self.constraints.get(str(constraint_id), {}).get('enabled', False)

    def get_type(self, constraint_id):
        """Mengambil tipe constraint (hard/soft)."""
        return self.constraints.get(str(constraint_id), {}).get('type', None)

    def get_description(self, constraint_id):
        """Mengambil deskripsi constraint."""
        return self.constraints.get(str(constraint_id), {}).get('description', None)

    def get_all_enabled(self):
        """Mengembalikan list ID dari semua constraint yang aktif."""
        return [cid for cid, val in self.constraints.items() if val.get('enabled', False)]