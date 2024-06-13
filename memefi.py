import aiohttp
import asyncio
import json
import os
import pytz
import random
import string
import time
from datetime import datetime
from urllib.parse import unquote
from utils.headers import headers_set
from utils.queries import QUERY_BOOSTER, QUERY_BOT_CLAIM, QUERY_BOT_START, QUERY_NEXT_BOSS, QUERY_USER, QUERY_LOGIN, MUTATION_GAME_PROCESS_TAPS_BATCH
from utils.queries import QUERY_TASK_VERIF, QUERY_TASK_COMPLETED, QUERY_GET_TASK, QUERY_TASK_ID, QUERY_GAME_CONFIG

url = "https://api-gw-tg.memefi.club/graphql"

token_index = 0
turbo_time = 0
turbo_status = False
token_fresh = ""
with open('query_id.txt', 'r') as file:
    lines = file.readlines()

def generate_random_nonce(length=52):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


# Mendapatkan akses token
async def fetch(account_line):
    with open('query_id.txt', 'r') as file:
        lines = file.readlines()
        raw_data = lines[account_line - 1].strip()

    tg_web_data = unquote(unquote(raw_data))
    query_id = tg_web_data.split('query_id=', maxsplit=1)[1].split('&user', maxsplit=1)[0]
    user_data = tg_web_data.split('user=', maxsplit=1)[1].split('&auth_date', maxsplit=1)[0]
    auth_date = tg_web_data.split('auth_date=', maxsplit=1)[1].split('&hash', maxsplit=1)[0]
    hash_ = tg_web_data.split('hash=', maxsplit=1)[1].split('&', maxsplit=1)[0]

    user_data_dict = json.loads(unquote(user_data))

    url = 'https://api-gw-tg.memefi.club/graphql'
    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    data = {
        "operationName": "MutationTelegramUserLogin",
        "variables": {
            "webAppData": {
                "auth_date": int(auth_date),
                "hash": hash_,
                "query_id": query_id,
                "checkDataString": f"auth_date={auth_date}\nquery_id={query_id}\nuser={unquote(user_data)}",
                "user": {
                    "id": user_data_dict["id"],
                    "allows_write_to_pm": user_data_dict["allows_write_to_pm"],
                    "first_name": user_data_dict["first_name"],
                    "last_name": user_data_dict["last_name"],
                    "username": user_data_dict.get("username", "Username gak diset"),
                    "language_code": user_data_dict["language_code"],
                    "version": "7.2",
                    "platform": "ios"
                }
            }
        },
        "query": QUERY_LOGIN
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            try:
                json_response = await response.json()
                if 'errors' in json_response:
                    # print("Query ID Salah")
                    return None
                else:
                    access_token = json_response['data']['telegramUserLogin']['access_token']
                    return access_token
            except aiohttp.ContentTypeError:
                print("Failed to decode JSON response")
                return None

# Cek akses token
async def cek_user(index):
    access_token = await fetch(index + 1)
    url = "https://api-gw-tg.memefi.club/graphql"

    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    headers['Authorization'] = f'Bearer {access_token}'
    
    json_payload = {
        "operationName": "QueryTelegramUserMe",
        "variables": {},
        "query": QUERY_USER
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=json_payload) as response:
            if response.status == 200:
                response_data = await response.json()
                if 'errors' in response_data:
                    print(f" Gagal Query ID Salah")
                    return None
                else:
                    user_data = response_data['data']['telegramUserMe']
                    return user_data  
            else:
                print(response)
                print(f" Gagal dengan status {response.status}, mencoba lagi...")
                return None 

async def submit_taps(index, total_tap):
    global token_fresh
    if token_fresh == "":
        token_fresh = await fetch(index + 1)
        print("set token fresh")
    
    access_token = token_fresh
    url = "https://api-gw-tg.memefi.club/graphql"
    json_payload = {
                        "operationName": "MutationGameProcessTapsBatch",
                        "variables": {
                            "payload": {
                                "nonce": generate_random_nonce(),
                                "tapsCount": total_tap
                            }
                        },
                        "query": MUTATION_GAME_PROCESS_TAPS_BATCH
                    }
    
   

    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    headers['Authorization'] = f'Bearer {access_token}'
    print(f"total Taps {total_tap}")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=json_payload) as response:
            if response.status == 200:
                response_data = await response.json()
                return response_data['data']  # Mengembalikan hasil response
            else:
                print(f" Gagal Tap dengan status {response.status}, mencoba lagi...")
                return None  # Mengembalikan respons error
# cek stat
async def cek_stat(index,headers):
    access_token = await fetch(index + 1)
    url = "https://api-gw-tg.memefi.club/graphql"

    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    headers['Authorization'] = f'Bearer {access_token}'
    
    json_payload = {
        "operationName": "QUERY_GAME_CONFIG",
        "variables": {},
        "query": QUERY_GAME_CONFIG
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=json_payload) as response:
            if response.status == 200:
                response_data = await response.json()
                if 'errors' in response_data:
                    return None
                else:
                    user_data = response_data['data']['telegramGameGetConfig']
                    return user_data
                
            elif response.start == 500:
                return response
            
            else:
                print(response)
                print(f" Gagal dengan status {response.status}, mencoba lagi...")
                return None, None  # Mengembalikan None jika terjadi error

async def check_and_complete_tasks(index, headers):
    # if tasks_completed.get(account_number, False):
    #     print(f"[ Akun {account_number + 1} ] Semua tugas telah selesai. Tidak perlu cek lagi. ✅")
    #     return True
    access_token = await fetch(index + 1)
    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    headers['Authorization'] = f'Bearer {access_token}'
    task_list_payload = {
        "operationName": "GetTasksList",
        "variables": {"campaignId": "50ef967e-dd9b-4bd8-9a19-5d79d7925454"},
        "query": QUERY_GET_TASK
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=task_list_payload, headers=headers) as response:
            if response.status != 200:
                # Menampilkan status dan respons jika bukan 200 OK
                print(f" Gagal dengan status {response.status}")
                print(await response.text())  # Menampilkan respons teks untuk debugging
                return False

            try:
                tasks = await response.json()
            except aiohttp.ContentTypeError:
                print("Gagal mengurai JSON, cek respons server.")
                return False

            # Lanjutkan dengan logika yang ada jika tidak ada error
            all_completed = all(task['status'] == 'Completed' for task in tasks['data']['campaignTasks'])
            if all_completed:
                print(f"\r[ Akun {index + 1} ] Semua tugas telah selesai. ✅            ",flush=True)
                return True


            print(f"\n[ Akun {index + 1} ]\nList Task:\n")
            for task in tasks['data']['campaignTasks']:
                print(f"{task['name']} | {task['status']}")

                if task['name'] == "Follow telegram channel" and task['status'] == "Pending":
                    print(f"⏩ Skipping task: {task['name']}")
                    continue  # Skip task jika nama task adalah "Follow telegram channel" dan statusnya "Pending"

                if task['status'] == "Pending":
                    print(f"\r🔍 Viewing task: {task['name']}", end="", flush=True)
                    view_task_payload = {
                        "operationName": "GetTaskById",
                        "variables": {"taskId": task['id']},
                        "query": QUERY_TASK_ID
                    }
                    async with session.post(url, json=view_task_payload, headers=headers) as view_response:
                        view_result = await view_response.json()

                        if 'errors' in view_result:
                            print(f"\r❌ Gagal mendapatkan detail task: {task['name']}")
                        else:
                            task_details = view_result['data']['campaignTaskGetConfig']
                            print(f"\r🔍 Detail Task: {task_details['name']}", end="", flush=True)

                    await asyncio.sleep(2)  # Jeda 2 detik setelah melihat detail

                    print(f"\r🔍 Verifikasi task: {task['name']}                                                                ", end="", flush=True)
                    verify_task_payload = {
                        "operationName": "CampaignTaskToVerification",
                        "variables": {"userTaskId": task['userTaskId']},
                        "query": QUERY_TASK_VERIF
                    }
                    async with session.post(url, json=verify_task_payload, headers=headers) as verify_response:
                        verify_result = await verify_response.json()

                        if 'errors' not in verify_result:
                            print(f"\r✅ {task['name']} | Moved to Verification", flush=True)
                        else:
                            print(f"\r❌ {task['name']} | Failed to move to Verification", flush=True)

                    await asyncio.sleep(2)  # Jeda 2 detik setelah verifikasi

            # Cek ulang task setelah memindahkan ke verification
            async with session.post(url, json=task_list_payload, headers=headers) as response:
                updated_tasks = await response.json()

                print("\nUpdated Task List After Verification:\n")
                for task in updated_tasks['data']['campaignTasks']:
                    print(f"{task['name']} | {task['status']}")
                    if task['status'] == "Verification":
                        print(f"\r🔥 Menyelesaikan task: {task['name']}", end="", flush=True)
                        complete_task_payload = {
                            "operationName": "CampaignTaskCompleted",
                            "variables": {"userTaskId": task['userTaskId']},
                            "query": QUERY_TASK_COMPLETED
                        }
                        async with session.post(url, json=complete_task_payload, headers=headers) as complete_response:
                            complete_result = await complete_response.json()

                            if 'errors' not in complete_result:
                                print(f"\r✅ {task['name']} | Completed                         ", flush=True)
                            else:
                                print(f"\r❌ {task['name']} | Failed to complete            ", flush=True)
                    
                    await asyncio.sleep(3)  # Jeda 3 detik setelah menyelesaikan tugas

    return False

async def change_boss(index):
    global token_fresh
    if token_fresh == "":
        token_fresh = await fetch(index + 1)
        print("set token fresh")
    
    access_token = token_fresh
    url = "https://api-gw-tg.memefi.club/graphql"
    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    headers['Authorization'] = f'Bearer {access_token}'
    json_payload = {
        "operationName": "telegramGameSetNextBoss",
        "variables": {},
        "query": QUERY_NEXT_BOSS
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json_payload, headers=headers) as response:
            if response.status == 200:
                print("Change boss done")
            else:
                print("Change boss error")
    await asyncio.sleep(1)

async def start_bot(index):
    global token_fresh
    if token_fresh == "":
        token_fresh = await fetch(index + 1)
        print("set token fresh")
    access_token = token_fresh
    url = "https://api-gw-tg.memefi.club/graphql"
    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    headers['Authorization'] = f'Bearer {access_token}'
    json_payload = {
        "operationName": "TapbotStart",
        "variables": {},
        "query": QUERY_BOT_START
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json_payload, headers=headers) as response:
            jsons = await response.json()
            if response.status == 200:
                print("start bot done")
                return response
            else:
                print("start bot done")
                return None

async def claim_bot(index):
    global token_fresh
    if token_fresh == "":
        token_fresh = await fetch(index + 1)
        print("set token fresh")
    
    access_token = token_fresh
    url = "https://api-gw-tg.memefi.club/graphql"
    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    headers['Authorization'] = f'Bearer {access_token}'
    json_payload = {
        "operationName": "TapbotClaim",
        "variables": {},
        "query": QUERY_BOT_CLAIM
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json_payload, headers=headers) as response:
            jsons = await response.json()
            if response.status == 200:
                print("claim bot done")
                return response
            else:
                print("claim bot done")
                return None

def print_welcome_message(serial=None):
    print(r"""
              
            Created By Snail S4NS Group
    find new airdrop & bot here: t.me/sanscryptox
              
          """)
    print()
    if serial is not None:
        print(f"Copy, tag bot @SnailHelperBot and paste this key in discussion group t.me/sanscryptox")
        print(f"Your key : {serial}")
async def apply_boost(index, boost_type):
    global token_fresh
    if token_fresh == "":
        token_fresh = await fetch(index + 1)
        print("set token fresh")
    
    access_token = token_fresh
    url = "https://api-gw-tg.memefi.club/graphql"

    headers = headers_set.copy()  # Membuat salinan headers_set agar tidak mengubah variabel global
    headers['Authorization'] = f'Bearer {access_token}'
    json_payload = {
        "operationName": "telegramGameActivateBooster",
        "variables": {"boosterType" : boost_type},
        "query": QUERY_BOOSTER
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json_payload, headers=headers) as response:
            if response.status == 200:
                print(f"boost applied {boost_type}")
            else:
                print("boost error")

async def main():

    print_welcome_message()
    while True:
        auto_use_booster = input("Auto use booster turbo and recharge energy ? (default n) (y/n): ").strip().lower()
        if auto_use_booster in ['y', 'n', '']:
            auto_use_booster = auto_use_booster or 'n'
            break
        else:
            print("Masukkan 'y' atau 'n'.")

    while True:
        auto_claim_bot = input("Auto Claim bot ? (default n) (y/n): ").strip().lower()
        if auto_claim_bot in ['y', 'n', '']:
            auto_claim_bot = auto_claim_bot or 'n'
            break
        else:
            print("Masukkan 'y' atau 'n'.")

    print("Starting Memefi bot...")
    global token_index, turbo_status, turbo_time, token_fresh
    while True:
      
        for index, line in enumerate(lines):
            result = await cek_user(token_index)
            if result is not None:
                first_name = result.get('firstName', 'Unknown')
                last_name = result.get('lastName', 'Unknown')
                league = result.get('league', 'Unknown')
                # accounts.append((token_index, result, first_name, last_name, league))
            else:
                print(f"Akun {token_index + 1}: Token tidak valid atau terjadi kesalahan")
            headers = {'Authorization': f'Bearer {result}'}
            # await check_and_complete_tasks(index, headers)
            stat_result = await cek_stat(token_index, headers)

            if stat_result is not None:
                user_data = stat_result                
                energy_sekarang = user_data['currentEnergy']
                boost_energy_amount = user_data['freeBoosts']['currentRefillEnergyAmount']
                boost_turbo_amount = user_data['freeBoosts']['currentTurboAmount']
                boss_health = user_data['currentBoss']['currentHealth']
                current_level_boss = user_data['currentBoss']['level']
                
                print(f"[ +++++ Akun {token_index + 1} - {first_name} {last_name} +++++]")
                print()
                print(f"Balance : {user_data['coinsAmount']} | Energy : {user_data['currentEnergy']} - {user_data['maxEnergy']}")
                print()
                if auto_claim_bot == 'y':
                    claim_bot_data = await claim_bot(token_index)
                    if claim_bot_data is None:
                        time.sleep(5)
                        continue
                    time.sleep(5)

                    start_bot_data = await start_bot(token_index)
                    if start_bot_data is None:
                        time.sleep(5)
                        continue
                    time.sleep(5)

                if current_level_boss == 11:
                    print("Boss max level", flush=True)
                    token_fresh = ""
                    token_index = (token_index + 1) % len(lines)
                    print()
                    time.sleep(5)
                    continue
                print(f"Free Turbo : {user_data['freeBoosts']['currentTurboAmount']} Free Energy : {user_data['freeBoosts']['currentRefillEnergyAmount']}")
                print()
                print(f"Boss level : {user_data['currentBoss']['level']} | Boss health : {user_data['currentBoss']['currentHealth']} - {user_data['currentBoss']['maxHealth']}")
                print()

                if boss_health <= 0:
                    await change_boss(token_index)

                if auto_use_booster == 'y':  
                    if energy_sekarang < 300:
                        if boost_energy_amount > 0:
                            boost_type = "Recharge"
                            await apply_boost(token_index, boost_type)
                        else:
                            print("\r🪫 Energy Habis, tidak ada booster tersedia. Beralih ke akun berikutnya.\n", flush=True)
                            token_fresh = ""
                            token_index = (token_index + 1) % len(lines)
                    else:
                        if(turbo_status == False):
                            while True:
                                total_tap = random.randint(10, 50)
                                respon = await submit_taps(token_index, total_tap)

                                if respon is not None:
                                    print(f"\rTapped ")
                                    energy = respon['telegramGameProcessTapsBatch']['currentEnergy']
                                    current_boss = respon['telegramGameProcessTapsBatch']['currentBoss']['currentHealth']
                                    print(f"current energy : {energy} - current health boss : {current_boss}")
                                else:
                                    print(f"failed status {respon}, mencoba lagi...")
                                    break
                
                                if current_boss <= 0:
                                    break

                                if energy < 300:
                                    print("Energy is less than 300. Stopping the loop.")
                                    break

                                if(boost_turbo_amount > 0):
                                    print("masuk turbo")
                                    boost_type = "Turbo"
                                    await apply_boost(token_index, boost_type)
                                    turbo_status = True
                                    turbo_time = time.time()
                                    break

                                time.sleep(2)
                        else:
                            while True:
                                total_tap = random.randint(20, 100)
                                respon = await submit_taps(token_index, total_tap)
                                
                                if respon is not None:
                                    print(f"Tapped")
                                    # print(respon)
                                    energy = respon['telegramGameProcessTapsBatch']['currentEnergy']
                                    current_boss = respon['telegramGameProcessTapsBatch']['currentBoss']['currentHealth']
                                    print(f"current energy : {energy} - current health boss : {current_boss}")
                                else:
                                    print(f" Gagal dengan status {respon}, mencoba lagi...")
                                    break
                                
                                if current_boss <= 0:
                                    await change_boss(token_index)
                                    
                                if ((time.time() - turbo_time) > 10):
                                    turbo_status = False
                                    turbo_time = 0
                                    break

                                time.sleep(2)
                else:
                    if energy_sekarang < 300:
                        total_tap = random.randint(10, 50)
                        respon = await submit_taps(token_index, total_tap)

                        if respon is not None:
                            print(f"\rTapped ")
                            energy = respon['telegramGameProcessTapsBatch']['currentEnergy']
                            current_boss = respon['telegramGameProcessTapsBatch']['currentBoss']['currentHealth']
                            print(f"current energy : {energy} - current health boss : {current_boss}")
                        else:
                            print(f"failed status {respon}, mencoba lagi...")
                            break
                
                        if current_boss <= 0:
                            break

                        time.sleep(2)
                    else:
                        print("\r🪫 Energy Habis, tidak ada booster tersedia. Beralih ke akun berikutnya.\n", flush=True)
                        token_fresh = ""
                        token_index = (token_index + 1) % len(lines)
                        time.sleep(2)

            print("=== [ MOVE PROCESSING ] ===")
            time.sleep(10)
        print("ALL ID DONE")
        print()
        now = datetime.now().isoformat(" ").split(".")[0]
        print(f"{now} | waiting 60 min")
        time.sleep(3600)
        # animate_energy_recharge(5)   
        
def animate_energy_recharge(duration):
    frames = ["|", "/", "-", "\\"]
    end_time = time.time() + duration
    while time.time() < end_time:
        remaining_time = int(end_time - time.time())
        for frame in frames:
            print(f"\r🪫 Mengisi ulang energi {frame} - Tersisa {remaining_time} detik         ", end="", flush=True)
            time.sleep(0.25)
    print("\r🔋 Pengisian energi selesai.                            ", flush=True)     

# Jalankan fungsi main() dan simpan hasilnya
asyncio.run(main())