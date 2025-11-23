def migrate(cr, version):
    """Migrer le champ marque (Char) vers marque_id (Many2one)"""
    
    # Vérifier si la colonne marque existe
    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='location_vehicule' 
            AND column_name='marque'
        )
    """)
    
    if cr.fetchone()[0]:
        # Renommer la colonne
        cr.execute("ALTER TABLE location_vehicule RENAME COLUMN marque TO marque_temp")
        
        # Créer les marques automatiquement si elles n'existent pas
        cr.execute("""
            INSERT INTO location_marque (name, code, actif, create_date, write_date, create_uid, write_uid)
            SELECT DISTINCT marque_temp, 
                   UPPER(SUBSTRING(marque_temp, 1, 3)),
                   TRUE,
                   NOW(),
                   NOW(),
                   1,
                   1
            FROM location_vehicule
            WHERE marque_temp IS NOT NULL
            ON CONFLICT (name) DO NOTHING
        """)
        
        # Ajouter la colonne marque_id
        cr.execute("ALTER TABLE location_vehicule ADD COLUMN marque_id INTEGER")
        
        # Mettre à jour les références
        cr.execute("""
            UPDATE location_vehicule v
            SET marque_id = m.id
            FROM location_marque m
            WHERE v.marque_temp = m.name
        """)
        
        # Supprimer la colonne temporaire
        cr.execute("ALTER TABLE location_vehicule DROP COLUMN marque_temp")
