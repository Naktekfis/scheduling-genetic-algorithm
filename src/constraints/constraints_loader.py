import pandas as pd

class ConstraintLoader:
    def __init__(self, csv_path):
        self.constraints = {}
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            self.constraints[row['ConstraintID']] = {
                'type': row['Type'],
                'description': row['Description'],
                'enabled': bool(row['Enabled'])
            }

    def is_enabled(self, constraint_id):
        return self.constraints.get(constraint_id, {}).get('enabled', False)

    def get_type(self, constraint_id):
        return self.constraints.get(constraint_id, {}).get('type', None)

    def get_description(self, constraint_id):
        return self.constraints.get(constraint_id, {}).get('description', None)

    def get_all_enabled(self):
        return [cid for cid, val in self.constraints.items() if val['enabled']]