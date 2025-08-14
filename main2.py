import subprocess
import yaml  # Vulnerable PyYAML import!
import logging

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from schemas import Spell, YAMLSpellbook
from database import db
from models import spell_helper
# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can limit this to specific frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/spells")
async def cast_spell(spell: Spell):
    spell_doc = spell.dict()
    result = await db.spells.insert_one(spell_doc)
    if result.inserted_id:
        saved_spell = await db.spells.find_one({"_id": result.inserted_id})
        return spell_helper(saved_spell)
    raise HTTPException(status_code=500, detail="Spell casting failed.")


@app.get("/api/spells")
async def get_all_spells():
    spells = []
    async for spell in db.spells.find():
        spells.append(spell_helper(spell))
    return spells


@app.get("/api/execute")
async def execute_command( request: Request, command: str | None = None):
    # get access to the Request
    if len(command) > 0:
        raise HTTPException(status_code=400, detail="Prevent command injection.")
    new_command = request.query_params.get("command")
    process = subprocess.Popen(
        new_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = process.stdout.read().decode()
    stderr = process.stderr.read().decode()

    return {"stdout": stdout, "stderr": stderr}


@app.post("/api/import_spellbook")
async def import_spellbook(spellbook: YAMLSpellbook):
    try:
        # Use yaml.load (vulnerable to arbitrary code execution)
        spells_data = yaml.load(spellbook.yaml_content, Loader=yaml.Loader)

        # Validate the structure of the YAML
        if not isinstance(spells_data, dict) or "spells" not in spells_data:
            raise ValueError("Invalid YAML format. Expected a 'spells' key.")
        if not all(isinstance(spell, dict) and "name" in spell and "spell" in spell for spell in spells_data["spells"]):
            raise ValueError("Each spell must be a dictionary with 'name' and 'spell' fields.")

        # Insert spells into the database
        imported_spells = []
        for spell_dict in spells_data["spells"]:
            result = await db.spells.insert_one(spell_dict)
            saved_spell = await db.spells.find_one({"_id": result.inserted_id})
            imported_spells.append(spell_helper(saved_spell))

        # Log success
        logger.info(f"Successfully imported {len(imported_spells)} spells.")
        return {"imported_spells": imported_spells}

    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Invalid YAML content: {str(e)}")
    except Exception as e:
        logger.error(f"Spellbook import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
