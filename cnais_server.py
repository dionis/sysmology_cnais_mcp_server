import json
import os
import asyncio
from typing import List, Optional

# En la plataforma Horizon (de Julep/Prefect), el entorno asíncrono choca con la librería oficial
# 'mcp.server.fastmcp' ya que Horizon espera su propia implementación 'fastmcp'.
# Esta sintaxis garantiza que en Horizon use la compatible, y evite el error en cli.py
try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

import httpx
from bs4 import BeautifulSoup
import yaml
import markdownify

# Initialize the FastMCP server
mcp = FastMCP("Sysmology CNAIS", instructions="You are a helpful assistant that provides information about seismology in Cuba. Get information about the last perceptible earthquake in Cuba, the last 7 days earthquakes in Cuba, the European Macroseismic Scale 1998 and what to do before, during, and after an earthquake. Use the tools below to get the information.")


@mcp.tool()
async def get_last_perceptible_earthquake(format: str = "JSON") -> str:
    """Gets the data of the last perceptible earthquake in Cuba, fetched from CENAIS.
    
    Args:
        format: The desired output format, either "JSON" or "YAML". Defaults to "JSON".
    """
    url = "https://www.cenais.gob.cu/rednacional/heli/lastfelt.html"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(verify=False, headers=headers, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            response.encoding = 'utf-8'
            html_content = response.text
    except Exception as e:
        return f"Error fetching the earthquake data: {str(e)}"
        
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {}
    
    key_map = {
        "tiempo_origen_utc": "origin_time_utc",
        "latitud": "latitude",
        "longitud": "longitude",
        "profundidad": "depth",
        "magnitud": "magnitude",
        "ubicado_a": "location"
    }
    
    h1_tags = soup.find_all('h1')
    for h1 in h1_tags:
        text = h1.get_text(strip=True)
        if text.startswith("Ocurrido:"):
            data["occurred_at"] = text.replace("Ocurrido:", "").strip()
        elif text.startswith("Tiempo Transcurrido:"):
            data["elapsed_time"] = text.replace("Tiempo Transcurrido:", "").strip()
            
    table = soup.find('table', {'id': 't01'})
    if table:
        for row in table.find_all('tr'):
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 2:
                key = cols[0].get_text(strip=True).replace(":", "")
                if key == "Parámetro":
                    continue
                    
                val = cols[1].get_text(separator=" ", strip=True)
                
                # Check for uncertainty in 3rd col
                uncertainty = None
                if len(cols) >= 3 and cols[2].name == 'td':
                    inc_text = cols[2].get_text(strip=True)
                    if inc_text and not row.find('img'):
                        uncertainty = inc_text.replace("±", "").replace("&#177;", "").strip()
                
                raw_key = key.lower().replace(" ", "_").replace("(", "").replace(")", "")
                eng_key = key_map.get(raw_key, raw_key)
                
                data[eng_key] = {
                    "value": val,
                    "uncertainty": uncertainty
                } if uncertainty else val

    if format.upper() == "YAML":
        return yaml.dump(data, allow_unicode=True, sort_keys=False)
    else:
        return json.dumps(data, indent=2, ensure_ascii=False)

@mcp.tool()
async def get_last_earthquake_last7days(format: str = "JSON") -> str:
    """Gets the data of the earthquakes happened in the last 7 days in Cuba, fetched from CENAIS.
    
    Args:
        format: The desired output format, either "JSON" or "YAML". Defaults to "JSON".
    """
    url = "https://www.cenais.gob.cu/lastquake/php/lastweek.php"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(verify=False, headers=headers, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            response.encoding = 'utf-8'
            data = response.json()
    except Exception as e:
        return f"Error fetching the earthquake data: {str(e)}"
        
    if not isinstance(data, list):
        return "Error: Unexpected data format received from the server."
        
    key_map = {
        "tiempoutc": "time_utc",
        "tiempolocal": "time_local",
        "longitud": "longitude",
        "latitud": "latitude",
        "profundidad": "depth",
        "magnitud": "magnitude",
        "distancialocalidad": "distance_to_location",
        "orientacion": "direction",
        "nombre": "location_name",
        "provincia": "province"
    }
    
    mapped_data = []
    for item in data:
        mapped_item = {}
        for k, v in item.items():
            eng_key = key_map.get(k, k)
            mapped_item[eng_key] = v
        mapped_data.append(mapped_item)

    if format.upper() == "YAML":
        return yaml.dump(mapped_data, allow_unicode=True, sort_keys=False)
    else:
        return json.dumps(mapped_data, indent=2, ensure_ascii=False)

@mcp.resource("cenais://ems98")
async def get_ems98_info() -> str:
    """Get European Macroseismic Scale 1998 Information dynamically from CENAIS."""
    url = "https://www.cenais.gob.cu/cenais/?page_id=120"
    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find(lambda tag: tag.name in ['h1','h2','h3','h4','strong'] and 'Europea 1998' in tag.text)
        
        if not title:
            return "Error: Could not locate the information on the source page."
            
        parent = title.parent
        # Traverse up until we capture the full content div
        while parent and len(parent.text) < 1000:
            parent = parent.parent
            
        if not parent:
            return "Error: Could not extract the content structurally."
            
        return markdownify.markdownify(str(parent)).strip()
    except Exception as e:
        return f"Error fetching information: {str(e)}"

@mcp.resource("cenais://what_to_do_in_earthquake")
async def get_what_to_do_in_earthquake() -> str:
    """Guidelines on what to do before, during, and after an earthquake dynamically from CENAIS."""
    url = "https://www.cenais.gob.cu/cenais/?page_id=86"
    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find(lambda tag: tag.name in ['h1','h2','h3','h4','strong'] and 'antes, durante y des' in tag.text.lower())
        
        if not title:
            return "Error: Could not locate the information on the source page."
            
        parent = title.parent
        # Traverse up until we capture the full content div
        while parent and len(parent.text) < 1000:
            parent = parent.parent
            
        if not parent:
            return "Error: Could not extract the content structurally."
            
        return markdownify.markdownify(str(parent)).strip()
    except Exception as e:
        return f"Error fetching information: {str(e)}"

if __name__ == "__main__":
    # Start the server using http
    mcp.run(transport="streamable-http")