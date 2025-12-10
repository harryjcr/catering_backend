"""seed sanitary control data

Revision ID: 008_seed_sanitary_control_data
Revises: 007_create_sanitary_control_tables
Create Date: 2024-12-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    # Define table structures for data insertion
    sanitary_policies = table(
        "sanitary_policies",
        column("id", postgresql.UUID),
        column("name", sa.String),
        column("description", sa.Text),
        column("is_active", sa.Boolean),
    )

    sanitary_companies = table(
        "sanitary_companies",
        column("id", postgresql.UUID),
        column("business_name", sa.String),
        column("ruc", sa.String),
        column("phone", sa.String),
        column("email", sa.String),
    )

    sanitary_incident_types = table(
        "sanitary_incident_types",
        column("id", postgresql.UUID),
        column("policy_id", postgresql.UUID),
        column("name", sa.String),
        column("description", sa.Text),
        column("is_active", sa.Boolean),
    )

    # =========================
    # Insert Policies
    # =========================
    policy_pest_id = uuid.uuid4()
    policy_waste_id = uuid.uuid4()
    policy_dining_id = uuid.uuid4()

    op.bulk_insert(
        sanitary_policies,
        [
            {
                "id": policy_pest_id,
                "name": "Control de Plagas",
                "description": "Inspección y control de plagas en las instalaciones del comedor",
                "is_active": True,
            },
            {
                "id": policy_waste_id,
                "name": "Manejo de Residuos",
                "description": "Gestión adecuada de residuos sólidos y líquidos",
                "is_active": True,
            },
            {
                "id": policy_dining_id,
                "name": "Saneamiento del Comedor",
                "description": "Limpieza y sanitización del área de comedor y cocina",
                "is_active": True,
            },
        ],
    )

    # =========================
    # Insert Companies
    # =========================
    op.bulk_insert(
        sanitary_companies,
        [
            # Pest Control Companies
            {
                "id": uuid.uuid4(),
                "business_name": "Fumigaciones El Escorpión SAC",
                "ruc": "20123456789",
                "phone": "965432178",
                "email": "ventas@escorpion.com",
            },
            {
                "id": uuid.uuid4(),
                "business_name": "Control de Plagas Profesional EIRL",
                "ruc": "20234567890",
                "phone": "987654321",
                "email": "contacto@controlplagas.pe",
            },
            # Waste Management Companies
            {
                "id": uuid.uuid4(),
                "business_name": "Ecogestión Residuos SAC",
                "ruc": "20456789123",
                "phone": "954321876",
                "email": "info@ecogestion.com",
            },
            {
                "id": uuid.uuid4(),
                "business_name": "Servicios de Residuos Ambientales SAC",
                "ruc": "20567890234",
                "phone": "976543210",
                "email": "ventas@residuosambientales.pe",
            },
            # Cleaning Companies
            {
                "id": uuid.uuid4(),
                "business_name": "Limpieza Total EIRL",
                "ruc": "20321654987",
                "phone": "943218765",
                "email": "contacto@limpiezatotal.com",
            },
            {
                "id": uuid.uuid4(),
                "business_name": "Sanitaria del Norte SAC",
                "ruc": "20789456123",
                "phone": "932187654",
                "email": "atencion@sanitarianorte.com",
            },
            {
                "id": uuid.uuid4(),
                "business_name": "Servicios de Limpieza Integral SAC",
                "ruc": "20678901345",
                "phone": "965123456",
                "email": "servicios@limpiezaintegral.pe",
            },
        ],
    )

    # =========================
    # Insert Incident Types
    # =========================

    # Pest Control Incident Types
    op.bulk_insert(
        sanitary_incident_types,
        [
            {
                "id": uuid.uuid4(),
                "policy_id": policy_pest_id,
                "name": "Plaga de cucarachas",
                "description": "Presencia de cucarachas en el área",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_pest_id,
                "name": "Plaga de roedores",
                "description": "Presencia de roedores en el área",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_pest_id,
                "name": "Plaga de hormigas",
                "description": "Presencia de hormigas en el área",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_pest_id,
                "name": "Plaga de moscas",
                "description": "Presencia excesiva de moscas",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_pest_id,
                "name": "Trampas sin funcionamiento",
                "description": "Trampas de control sin funcionar correctamente",
                "is_active": True,
            },
        ],
    )

    # Waste Management Incident Types
    op.bulk_insert(
        sanitary_incident_types,
        [
            {
                "id": uuid.uuid4(),
                "policy_id": policy_waste_id,
                "name": "Contenedores insuficientes",
                "description": "No hay suficientes contenedores de basura",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_waste_id,
                "name": "Contenedores llenos",
                "description": "Contenedores sobrepasando su capacidad",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_waste_id,
                "name": "Mal manejo de residuos orgánicos",
                "description": "Residuos orgánicos no segregados correctamente",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_waste_id,
                "name": "Falta de señalización",
                "description": "Contenedores sin identificación adecuada",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_waste_id,
                "name": "Olores fuertes",
                "description": "Presencia de malos olores por acumulación",
                "is_active": True,
            },
        ],
    )

    # Dining Sanitation Incident Types
    op.bulk_insert(
        sanitary_incident_types,
        [
            {
                "id": uuid.uuid4(),
                "policy_id": policy_dining_id,
                "name": "Superficies sucias",
                "description": "Mesas, sillas o mostradores con suciedad visible",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_dining_id,
                "name": "Utensilios mal lavados",
                "description": "Platos, cubiertos o vasos con residuos",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_dining_id,
                "name": "Área de cocina desordenada",
                "description": "Cocina sin orden o limpieza adecuada",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_dining_id,
                "name": "Pisos sucios o mojados",
                "description": "Pisos del comedor con suciedad o líquidos",
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "policy_id": policy_dining_id,
                "name": "Equipos sin sanitizar",
                "description": "Equipos de cocina sin limpieza profunda",
                "is_active": True,
            },
        ],
    )


def downgrade():
    # Delete seed data in reverse order
    op.execute("DELETE FROM sanitary_incident_types")
    op.execute("DELETE FROM sanitary_companies")
    op.execute("DELETE FROM sanitary_policies")
