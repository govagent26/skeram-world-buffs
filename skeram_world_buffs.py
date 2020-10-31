# bot.py
import os
import sys
import random
import re
import platform
import discord
import enum

from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pytz import timezone


# load all environment properties
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SKERAM_SERVER_ID = int(os.getenv('SKERAM_SERVER_ID'))
WORLD_BUFF_CHANNEL_ID = int(os.getenv('WORLD_BUFF_CHANNEL_ID'))
WBC_CHANNEL_ID = int(os.getenv('WBC_CHANNEL_ID'))
WORLD_BUFF_COORDINATOR_ROLE_ID = int(os.getenv('WORLD_BUFF_COORDINATOR_ROLE_ID'))
WORLD_BUFF_SELLER_ROLE_ID = int(os.getenv('WORLD_BUFF_SELLER_ROLE_ID'))
MASTER_ID = int(os.getenv('MASTER_ID'))
# debug flag for troubleshooting
DEBUG = True if os.getenv('DEBUG') == 'true' else False
# setting to bypass DM rights check and assume seller
DM_BYPASS_ASSUME_SELLER = True if os.getenv('DM_BYPASS_ASSUME_SELLER') == 'true' else False

PRINT_TIME_FORMAT = '%-I:%M%p' if platform.system() != 'Windows' else '%#I:%M%p'

# set constants
TIME_UNKNOWN = '?:??'
BVSF_CORRUPTED = '**CORRUPTED**'
WORLD_BUFF_COORDINATOR = 'WBC'
WORLD_BUFF_SELLER = 'WBS'
# minutes after a drop to be auto-removed
TIME_AFTER_DROP_TO_AUTO_REMOVE = 1

# setup intents to get member data for DMs
intents = discord.Intents.default()
intents.members = True

# initialize the discord bot
bot = commands.Bot(command_prefix=['--', '—', '-'], case_insensitive=True, intents=intents)
bot.remove_command('help')


# functions to add or update a service sellers info
async def add_update_service_seller(ctx, service, name, note_array):
    try:
        # 1. Clean and format input
        clean_title_name = remove_command_surrounding_special_characters(name).title()
        message = await construct_args_message(note_array)
        if len(message) > 30:
            # cap message length to 30 characters to avoid too much spamming
            message = message[:30]
        # 2. Check if service already posted
        seller = sellers.find_seller(service, name)
        if seller == None:
            # 2a. If not posted (find_seller == None) -> add flow
            await add_service_seller(ctx, service, clean_title_name, message)
        else:
            # 2b. If posted (find_seller != None) -> update flow
            await update_service_seller(ctx, service, seller, clean_title_name, message)
    finally:
        # debug ouput for testing/verification
        await debug_print_services()

async def add_service_seller(ctx, service, name, message):
    service_info = service.value
    # 3. No rights check needed
    # 4. Add seller for service (add_seller)
    sellers.add_seller(service, name, message, ctx.message.author.id)
    # 5. Post update to world-buff-chat channel
    await post_in_world_buffs_chat_channel()
    # 6. Playback that update was done
    await playback_message(ctx, '{0} buff timer updated to:\n{1}'.format(service_info.output_line_name, await service_info.output_function()))
    # 7. If update done via DM, post log record in wbc-commands channel
    await post_update_in_wbc_channel(ctx, 'Added a {0} {1} {2}'.format(service_info.icon, service_info.name, 'summoner' if service_info.summoner else 'buffer'), name, [message], '**{0} {1} - DM Update**'.format(service_info.icon, service_info.name))

async def update_service_seller(ctx, service, seller, name, message):
    service_info = service.value
    # 3. Check for rights, if a seller then author ID must match
    if not is_coordinator(ctx) and seller.author != '' and seller.author != ctx.message.author.id:
        # 3b. no rights -> playback message that no rights to update, return
        await playback_message(ctx, ':no_entry_sign: Missing Rights - only the user who added this service can update it')
        return
    # 4. Update message
    seller.msg = message
    # 5. Post update to world-buff-chat channels
    await post_in_world_buffs_chat_channel()
    # 6. Playback that update was done
    await playback_message(ctx, '{0} buff timer updated to:\n{1}'.format(service_info.output_line_name, await service_info.output_function()))
    # 7. If update done via DM, post log record in wbc-commands channel
    await post_update_in_wbc_channel(ctx, 'Updated message for a {0} {1} {2}'.format(service_info.icon, service_info.name, 'summoner' if service_info.summoner else 'buffer'), name, [message], '**{0} {1} - DM Update**'.format(service_info.icon, service_info.name))

# function to remove a service sellers info
async def remove_service_seller(ctx, service, name):
    try:
        service_info = service.value
        # 1. Clean and format input
        clean_title_name = remove_command_surrounding_special_characters(name).title()
        # 2. Check if service already posted
        seller = sellers.find_seller(service, name)
        if seller == None:
            # 2b. If not posted -> playback message that does not exist
            await playback_message(ctx, ':warning: User not currently posted - nothing to remove')
            return
        # 3. Check for rights, if a seller then author ID must match
        if not is_coordinator(ctx) and seller.author != '' and seller.author != ctx.message.author.id:
            # 3b. no rights -> playback message that no rights to remove, return
            await playback_message(ctx, ':no_entry_sign: Missing Rights - only the user who added this service can remove it')
            return
        # 4. Remove service listing
        sellers.remove_seller(service, seller)
        # 5. Post update to world-buff-chat channels
        await post_in_world_buffs_chat_channel()
        # 6. Playback that update was done
        output = await service_info.output_function()
        if (output != ''):
            await playback_message(ctx, '{0} buff timer updated to:\n{1}'.format(service_info.output_line_name, output))
        else:
            await playback_message(ctx, '{0} buff timer removed'.format(service_info.output_line_name))
        # 7. If update done via DM, post log record in wbc-commands channel
        await post_update_in_wbc_channel(ctx, 'Removed a {0} {1} {2}'.format(service_info.icon, service_info.name, 'summoner' if service_info.summoner else 'buffer'), name, header='**{0} {1} - DM Update**'.format(service_info.icon, service_info.name))
    finally:
        # debug ouput for testing/verification
        await debug_print_services()


# function to update a buff reset time
async def update_buff_time(ctx, buff, time):
    try:
        #  1. Clean and format input
        clean_time = await format_time(remove_command_surrounding_special_characters(time))
        #  2. Check if any drops posted match existing time
        dropper = buff.find_dropper(buff.time)
        #  2a. If drop found -> remove dropper
        if dropper != None:
            await ctx.send('Dropper found whose time matched old time, assuming a drop was done and removing dropper:\n  {0.time} (**{0.name}**)'.format(dropper))
            buff.remove_drop(dropper)
        #  3. Update time
        buff.time = clean_time
        #  4. Post update to world-buff-chat channel
        await post_in_world_buffs_chat_channel()
        #  5. Playback that update was donea
        await playback_message(ctx, '{0} buff timer updated to:\n{1}'.format(buff.name, await buff.output_function()))
        #  6. If update done via DM, post log record in wbc-commands channel
        ## FUTURE - TODO
    finally:
        # debug ouput for testing/verification
        await debug_print_drop_buffs(buff)


# functions to add or update a droppers drop info
async def add_update_drop_dropper(ctx, buff, name, time):
    try:
        # 1. Clean and format input
        clean_name_input = await format_time(remove_command_surrounding_special_characters(name))
        clean_time_input = await format_time(remove_command_surrounding_special_characters(time))
        actual_name = clean_name_input.title()
        actual_time = clean_time_input
        # support for reverse order params (when provided time is valid)
        if await validate_time_format(clean_name_input):
            actual_name = clean_time_input.title()
            actual_time = clean_name_input
        # 2. Check if dropper already posted
        dropper = buff.find_dropper(actual_name)
        if dropper == None:
            # try to find via time if no name matched
            dropper = buff.find_dropper(actual_time)
        if dropper == None:
            # 2a. If not posted (find_dropper == None) -> add flow
            await add_drop_dropper(ctx, buff, actual_name, actual_time)
        else:
            # 2b. If posted (find_dropper != None) -> update flow
            await update_drop_dropper(ctx, buff, dropper, actual_name, actual_time)
    finally:
        # debug ouput for testing/verification
        await debug_print_drop_buffs(buff)

async def add_drop_dropper(ctx, buff, name, time):
    # 3. Add drop for dropper (add_drop)
    buff.add_drop(time, name, ctx.message.author.id)
    # 4. Sort droppers
    buff.sort_drops()
    # 5. Post update to world-buff-chat channel
    await post_in_world_buffs_chat_channel()
    # 6. Playback that update was done
    await playback_message(ctx, '{0} buff timer updated to:\n{1}'.format(buff.name, await buff.output_function()))
    # 7. If update done via DM, post log record in wbc-commands channel
    ## FUTURE - TODO

async def update_drop_dropper(ctx, buff, dropper, name, time):
    # 3. Update name or time
    if dropper.name == name:
        # name matches, update time
        dropper.time = time
    else:
        # time matches, update name
        dropper.name = name
    # 4. Sort droppers
    buff.sort_drops()
    # 5. Post update to world-buff-chat channels
    await post_in_world_buffs_chat_channel()
    # 6. Playback that update was done
    await playback_message(ctx, '{0} buff timer updated to:\n{1}'.format(buff.name, await buff.output_function()))
    # 7. If update done via DM, post log record in wbc-commands channel
    ## FUTURE - TODO

# function to remove a buff dropper
async def remove_buff_dropper(ctx, buff, name_or_time):
    try:
        # 1. Clean and format input
        clean_name_or_time = await format_time(remove_command_surrounding_special_characters(name_or_time))
        # 2. Check if any drops posted match via name or time
        dropper = buff.find_dropper(clean_name_or_time)
        if dropper == None:
            # 2b. If drop not found -> playback message that does not exist
            await playback_message(ctx, ':warning: Dropper not currently posted - nothing to remove')
            return
        # 3. Remove dropper
        buff.remove_drop(dropper)
        # 4. Post update to world-buff-chat channels
        await post_in_world_buffs_chat_channel()
        # 5. Playback that update was done
        await playback_message(ctx, '{0} buff timer updated to:\n{1}'.format(buff.name, await buff.output_function()))
        # 6. If update done via DM, post log record in wbc-commands channel
        ## FUTURE - TODO
    finally:
        # debug ouput for testing/verification
        await debug_print_drop_buffs(buff)


# functions to check for the user's role on the server
def coordinator_or_seller(coordinator=True, seller=False):
    async def predicate(ctx):
        user_roles = check_for_role(ctx)
        return (coordinator and WORLD_BUFF_COORDINATOR in user_roles) or (seller and WORLD_BUFF_SELLER in user_roles)
    return commands.check(predicate)

def check_for_role(ctx):
    user_roles = []
    author = ''
    try:
        if (ctx.message.guild != None):
            # from server, get user info from message
            author = ctx.message.author
        else:
            if DM_BYPASS_ASSUME_SELLER:
                # in case need to bypass the DM rights check, assume seller
                user_roles.append(WORLD_BUFF_SELLER)
                return user_roles
            # DM, need to get server and get user info on server
            skeram_server = bot.get_guild(SKERAM_SERVER_ID)
            author = skeram_server.get_member(ctx.message.author.id)
            #author = discord.utils.get(skeram_server.members, id=ctx.message.author.id)
        # check for coordinator / seller roles
        for role in author.roles:
            if WORLD_BUFF_SELLER_ROLE_ID == role.id:
                user_roles.append(WORLD_BUFF_SELLER)
            if WORLD_BUFF_COORDINATOR_ROLE_ID == role.id:
                user_roles.append(WORLD_BUFF_COORDINATOR)
    finally:
        # debug ouput for testing/verification
        if DEBUG:
            print("Author={0}".format(author))
            print("Roles={0}".format(user_roles))
            sys.stdout.flush()
    return user_roles

def is_coordinator(ctx):
    user_roles = check_for_role(ctx)
    if WORLD_BUFF_COORDINATOR in user_roles:
        return True
    return False


# start of defined bot commands/functions
@bot.command(name="help", description="Prints this message of all commands - note when using commands, do not include < > [ ] - additionally all commands can be invoked using '--' or '-' or '—'")
@coordinator_or_seller(seller=True)
async def help(ctx):
    coordinator = is_coordinator(ctx)
    helptext = "```"
    for cog in bot.cogs:
        commands = ''
        cog_obj = bot.get_cog(cog)
        cog_obj_name = str(cog_obj)
        if not coordinator and not ('Summoner' in cog_obj_name or 'DMTBuff' in cog_obj_name):
            continue
        for command in cog_obj.get_commands():
            commands += '\n{0.command_prefix[0]}{1.qualified_name} {1.signature}'.format(bot, command)
        helptext += '{0}\n  {1.qualified_name}\n\n'.format(commands, cog_obj)
    if (coordinator):
        # help message too long - need to send commands and then final help text separate
        helptext += "```"
        await ctx.send(helptext)
        helptext = "```"
    helptext += '\n\n{0.command_prefix[0]}{1.qualified_name} {1.signature}\n  {1.description}\n\n'.format(bot, bot.get_command('help'))
    helptext += "```"
    await ctx.send(helptext)

@bot.command(name="playback", description="Updates if bot should print out when changes occur [on|off]")
async def playback(ctx, status):
    if (ctx.message.author.id != MASTER_ID):
        raise commands.CommandNotFound()
        return
    global playback_updates
    if status.lower() == 'on':
        playback_updates = True
    else:
        playback_updates = False
    await ctx.send('Playback is ' + ('enabled' if status == 'on' else 'disabled'))

@bot.command(name="clear-all-data-confirm", description="Purges all saved data")
async def clear_data(ctx):
    if (ctx.message.author.id != MASTER_ID):
        raise commands.CommandNotFound()
        return
    world_buff_channel = bot.get_channel(WORLD_BUFF_CHANNEL_ID)
    messages = await world_buff_channel.history(limit = 1).flatten()
    if len(messages) > 0 and messages[0].author == bot.user:
        message = await world_buff_channel.fetch_message(messages[0].id)
        await ctx.send('**Data cleared...**\nPrevious Message:\n' + message.content)
    await clear_all_data()
    await post_in_world_buffs_chat_channel()
    await ctx.send('All data cleared')
    # debug ouput for testing/verification
    await debug_print_services()

@bot.command(name="mockup-data-confirm", description="Populates all elements of the message with dummy data")
async def mockup_data(ctx):
    if (ctx.message.author.id != MASTER_ID):
        raise commands.CommandNotFound()
        return
    # clear all data prior to populating with dummy data
    await clear_all_data()
    # populate with dummy data
    global server_maintenance
    server_maintenance = 'SERVER IS UP'
    rend.time = '3:00pm'
    rend.add_drop('3:00pm', 'Renddropper')
    rend.add_drop('6:30pm', 'Nextdropper')
    ony.time = 'OPEN'
    ony.add_drop('8:45pm', 'Onydropper')
    nef.time = '7:45pm'
    hakkar.add_drop('7:00pm', 'Hakkardrop')
    hakkar.add_drop('9:15pm', 'Hakkarnotdrop')
    sellers.add_seller(Services.YI, 'YIsums', '5g', 1234567890)
    sellers.add_seller(Services.YI, 'YIsummer', '4g w/port')
    sellers.add_seller(Services.BB, 'BBsums', '', 1234567890)
    global bvsf_time
    bvsf_time = '4:35pm'
    sellers.add_seller(Services.BVSF, 'Whosums', '5g', 1234567890)
    sellers.add_seller(Services.DMTB, 'Mybuffs', '7g w/port and summons', 1234567890)
    sellers.add_seller(Services.DMTB, 'Dmtbuffs', '5g')
    sellers.add_seller(Services.DMTS, 'Datsums', '8g')
    sellers.add_seller(Services.NAXX, 'naxxsums', '7g')
    sellers.add_seller(Services.AQ, 'aqSums', '3g')
    sellers.add_seller(Services.BRM, 'brmsums', '7g', 1234567890)
    global dmf_location
    dmf_location = 'Mulgore'
    sellers.add_seller(Services.DMF, 'dmfsums', '10g', 1234567890)
    sellers.add_seller(Services.WICKERMAN, 'wickersums', '9g')
    global alliance
    alliance = 'ALLY everywhere - dont die'
    global extra_message
    extra_message = 'Extra message for ........'
    await post_in_world_buffs_chat_channel()
    await ctx.send('Data mocked up')
    # debug ouput for testing/verification
    await debug_print_services()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound) or isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send('**Unknown command entered or parameters are missing** - a list of commands and usage can be found using --help')
        return
    if isinstance(error, commands.errors.MissingRole) or isinstance(error, commands.errors.MissingAnyRole):
        await ctx.send('**Missing role to execute this command**')
        return
    raise error

@bot.event
async def on_ready():
    try:
        # always print when first loading up, debug or not
        print("BOT WAKING UP")
        sys.stdout.flush()
        # find the last message and see if it was from the bot to load data
        world_buff_channel = bot.get_channel(WORLD_BUFF_CHANNEL_ID)
        wbc_channel = bot.get_channel(WBC_CHANNEL_ID)
        messages = await world_buff_channel.history(limit = 1).flatten()
        if len(messages) > 0 and messages[0].author == bot.user:
            # message found, load data
            message = await world_buff_channel.fetch_message(messages[0].id)
            message_content = message.content
            populate_success = await populate_data_from_message(message_content)

            new_message = await get_buff_times()
            if not populate_success:
                await wbc_channel.send('**Bot restarted....**\nExisting Message:\n{0}\n\n\n'.format(message_content))
                await wbc_channel.send('New Message:\n{0}\n\nSome discrepencies may exist in existing vs new message after restart, please verify'.format(new_message))
            #else:
                #await wbc_channel.send('**Bot restarted....**\nworld-buff-times message reposted') 
            await message.edit(content = new_message)
        else:
            # no message found, nothing to load
            await wbc_channel.send('**Bot restarted....**\nNo exising message found, all data cleared')
    finally:
        global data_loaded
        data_loaded = True
        # debug ouput for testing/verification
        await debug_print_services()
        await debug_print_drop_buffs(rend)
        await debug_print_drop_buffs(ony)
        await debug_print_drop_buffs(nef)
        await debug_print_drop_buffs(hakkar)
        # always print when up and running, debug or not
        print("BOT STARTED UP AND READY")
        sys.stdout.flush()
    check_for_message_updates.start()


@tasks.loop(minutes=1)
async def check_for_message_updates():
    global rend
    global ony
    global nef
    global bvsf_time
    global bvsf_update_count
    post_updates = False
    wbc_channel = bot.get_channel(WBC_CHANNEL_ID)
    old_bvsf_time = bvsf_time
    if await check_for_bvsf_updates():
        embed = discord.Embed(title="**:wilted_rose: BVSF Buff Auto-Update**", color=0xc800ff)
        embed.add_field(name="Prior time:", value=old_bvsf_time, inline=True)
        if bvsf_update_count > 10:
            embed.description = "BVSF time in the past, but has not been manually verified/updated in over 4 hours - being cleared"
            bvsf_time = TIME_UNKNOWN
            bvsf_update_count = 0
        else:
            embed.description = "BVSF time in the past, being updated..."
            if bvsf_update_count > 5:
                embed.set_footer(text="Note that the time has not been manually verified/updated in over 2 hours...is it correct?")
        embed.add_field(name="Updated time: ", value=bvsf_time, inline=True)
        await wbc_channel.send(embed=embed)
        post_updates = True
    if await calc_minutes_since_time(rend.time) > TIME_AFTER_DROP_TO_AUTO_REMOVE:
        next_rend_time = await calculate_next_time(rend.time, 180+1)
        embed = discord.Embed(title="**:japanese_ogre: Rend Buff Auto-Update**", color=0xff0000)
        rend_dropper_removed = False
        for drop in rend.drops:
            if drop.time == rend.time:
                #old time found, remove dropper and add to embed
                embed.add_field(name="Dropper removed", value="{0.time} - (**{0.name}**)".format(drop), inline=False)
                rend.drops.remove(drop)
                rend_dropper_removed = True
        if rend_dropper_removed:
            embed.description = "Rend time in the past, matching dropper found - assuming it was dropped..."
            embed.add_field(name="Prior time:", value=rend.time, inline=True)
            embed.add_field(name="Updated time: ", value=next_rend_time, inline=True)
            rend.time = next_rend_time
        else:
            embed.description = "Rend time in the past, unknown if it is open or was dropped (no matching dropper found)"
            embed.add_field(name="Prior time:", value=rend.time, inline=True)
            embed.add_field(name="Updated time: ", value="OPEN??", inline=True)
            embed.add_field(name="----------", value="If a drop was done, next drop time may be around ~{0}".format(next_rend_time), inline=False)
            rend.time = 'OPEN??'
        await wbc_channel.send(embed=embed)
        post_updates = True
    elif await time_is_open(rend.time):
        for drop in rend.drops:
            if await calc_minutes_since_time(drop.time) > TIME_AFTER_DROP_TO_AUTO_REMOVE:
                next_rend_time = await calculate_next_time(drop.time, 180+1)
                embed = discord.Embed(title="**:japanese_ogre: Rend Buff Auto-Update**", description="Rend dropper time is in the past and rend is off CD, assuming a drop was done and updating...", color=0xff0000)
                embed.add_field(name="Dropper removed", value="{0.time} - (**{0.name}**)".format(drop), inline=False)
                embed.add_field(name="Prior time:", value=rend.time, inline=True)
                embed.add_field(name="Updated time: ", value=next_rend_time, inline=True)
                await wbc_channel.send(embed=embed)
                rend.time = next_rend_time
                rend.drops.remove(drop)
                post_updates = True
    if await calc_minutes_since_time(ony.time) > TIME_AFTER_DROP_TO_AUTO_REMOVE:
        next_ony_time = await calculate_next_time(ony.time, 360+1)
        embed = discord.Embed(title="**:dragon: Ony Buff Auto-Update**", color=0xc7ffa8)
        ony_dropper_removed = False
        for drop in ony.drops:
            if drop.time == ony.time:
                #old time found, remove dropper and add to embed
                embed.add_field(name="Dropper removed", value="{0.time} - (**{0.name}**)".format(drop), inline=False)
                ony.drops.remove(drop)
                ony_dropper_removed = True
        if ony_dropper_removed:
            embed.description = "Ony time in the past, matching dropper found - assuming it was dropped..."
            embed.add_field(name="Prior time:", value=ony.time, inline=True)
            embed.add_field(name="Updated time: ", value=next_ony_time, inline=True)
            ony.time = next_ony_time
        else:
            embed.description = "Ony time in the past, unknown if it is open or was dropped (no matching dropper found)"
            embed.add_field(name="Prior time:", value=ony.time, inline=True)
            embed.add_field(name="Updated time: ", value="OPEN??", inline=True)
            embed.add_field(name="----------", value="If a drop was done, next drop time may be around ~{0}".format(next_ony_time), inline=False)
            ony.time = 'OPEN??'
        await wbc_channel.send(embed=embed)
        post_updates = True
    elif await time_is_open(ony.time):
        for drop in ony.drops:
            if await calc_minutes_since_time(drop.time) > TIME_AFTER_DROP_TO_AUTO_REMOVE:
                next_ony_time = await calculate_next_time(drop.time, 360+1)
                embed = discord.Embed(title="**:dragon: Ony Buff Auto-Update**", description="Ony dropper time is in the past and ony is off CD, assuming a drop was done and updating...", color=0xc7ffa8)
                embed.add_field(name="Dropper removed", value="{0.time} - (**{0.name}**)".format(drop), inline=False)
                embed.add_field(name="Prior time:", value=ony.time, inline=True)
                embed.add_field(name="Updated time: ", value=next_ony_time, inline=True)
                await wbc_channel.send(embed=embed)
                ony.time = next_ony_time
                ony.drops.remove(drop)
                post_updates = True
    if await calc_minutes_since_time(nef.time) > TIME_AFTER_DROP_TO_AUTO_REMOVE:
        next_nef_time = await calculate_next_time(nef.time, 480+1)
        embed = discord.Embed(title="**:dragon_face: Nef Buff Auto-Update**", color=0x4f9c26)
        nef_dropper_removed = False
        for drop in nef.drops:
            if drop.time == nef.time:
                #old time found, remove dropper and add to embed
                embed.add_field(name="Dropper removed", value="{0.time} - (**{0.name}**)".format(drop), inline=False)
                nef.drops.remove(drop)
                nef_dropper_removed = True
        if nef_dropper_removed:
            embed.description = "Nef time in the past, matching dropper found - assuming it was dropped..."
            embed.add_field(name="Prior time:", value=nef.time, inline=True)
            embed.add_field(name="Updated time: ", value=next_nef_time, inline=True)
            nef.time = next_nef_time
        else:
            embed.description = "Nef time in the past, unknown if it is open or was dropped (no matching dropper found)"
            embed.add_field(name="Prior time:", value=nef.time, inline=True)
            embed.add_field(name="Updated time: ", value="OPEN??", inline=True)
            embed.add_field(name="----------", value="If a drop was done, next drop time may be around ~{0}".format(next_nef_time), inline=False)
            nef.time = 'OPEN??'
        await wbc_channel.send(embed=embed)
        post_updates = True
    elif await time_is_open(nef.time):
        for drop in nef.drops:
            if await calc_minutes_since_time(drop.time) > TIME_AFTER_DROP_TO_AUTO_REMOVE:
                next_nef_time = await calculate_next_time(drop.time, 480+1)
                embed = discord.Embed(title="**:dragon_face: Nef Buff Auto-Update**", description="Nef dropper time is in the past and nef is off CD, assuming a drop was done and updating...", color=0x4f9c26)
                embed.add_field(name="Dropper removed", value="{0.time} - (**{0.name}**)".format(drop), inline=False)
                embed.add_field(name="Prior time:", value=nef.time, inline=True)
                embed.add_field(name="Updated time: ", value=next_nef_time, inline=True)
                await wbc_channel.send(embed=embed)
                nef.time = next_nef_time
                nef.drops.remove(drop)
                post_updates = True
    for drop in hakkar.drops:
        if await calc_minutes_since_time(drop.time) > TIME_AFTER_DROP_TO_AUTO_REMOVE:
            embed = discord.Embed(title="**:heartpulse: Hakkar Buff Auto-Update**", description="Hakkar dropper time is in the past, assuming a drop was done and removing dropper...", color=0xe86969)
            embed.add_field(name="Dropper removed", value="{0.time} - (**{0.name}**)".format(drop), inline=False)
            await wbc_channel.send(embed=embed)
            hakkar.remove_drop(drop)
            post_updates = True
    if post_updates:
        await post_in_world_buffs_chat_channel()

@bot.event
async def on_message(message):
    if not data_loaded:
        # bot not loaded, don't accept messages yet
        return
    if message.channel.id != WBC_CHANNEL_ID and message.guild != None:
        # only read non-help messages from designated channel
        return
    await bot.process_commands(message)


class BuffAvailTimeCommands(commands.Cog, name='Specifies the <time> when the buff is open/off CD'):
    @commands.command(name='rend', aliases=['rend-time'], brief='Set time for when rend is open/off CD', help='Sets the next available time rend buff is open - example: --rend 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_rend_time(self, ctx, time):
        await update_buff_time(ctx, rend, time)

    @commands.command(name='ony', aliases=['ony-time'], brief='Set time for when ony is open/off CD', help='Sets the next available time ony buff is open - example: --ony 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_ony_time(self, ctx, time):
        await update_buff_time(ctx, ony, time)

    @commands.command(name='nef', aliases=['nef-time'], brief='Set time for when nef is open/off CD', help='Sets the next available time nef buff is open - example: --nef 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_nef_time(self, ctx, time):
        await update_buff_time(ctx, nef, time)


class BVSFBuffCommands(commands.Cog, name = 'Sets the next <time> the BVSF flower should be up or clears it'):
    @commands.command(name='bvsf', aliases=['bvsf-time'], brief='Set time when BVSF is up', help='Sets the next time bvsf flower buff is up - example: --bvsf 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_bvsf_time(self, ctx, time):
        global bvsf_time
        global bvsf_update_count
        clean_time = await format_time(remove_command_surrounding_special_characters(time))
        if await validate_time_format(clean_time):
            bvsf_time = clean_time
            bvsf_update_count = 0
            await post_in_world_buffs_chat_channel()
            await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())
        else:
            await ctx.send('Invalid time provided, format must be HH:MM[am|pm] - example: {0.prefix}{0.command.name} 2:54pm'.format(ctx))

    @commands.command(name='bvsf-corrupted', aliases=['bvsf-corrupt'], brief='Sets the BVSF as corrupted', help='Sets the flower as corrupted - example: --bvsf-corrupted')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_bvsf_corrupted(self, ctx):
        global bvsf_time
        bvsf_time = BVSF_CORRUPTED
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())

    @commands.command(name='bvsf-clear', brief='Clears BVSF time, sets to ?:??', help='Sets the BVSF time to ?:?? - example: --bvsf-clear')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def clear_bvsf_time(self, ctx):
        global bvsf_time
        bvsf_time = TIME_UNKNOWN
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'BVSF buff timer updated to:\n' + await calc_bvsf_msg())


class BuffDropAddCommands(commands.Cog, name='Adds the <name> of a buff dropper and the planned <time>'):
    def generate_dropper_aliases(drop):
        return ["{0}-drop-add".format(drop), "{0}-drops".format(drop), "{0}-drops-add".format(drop)]
        
    @commands.command(name='rend-drop', aliases=generate_dropper_aliases("rend"), help='Sets a rend confirmed dropper with time - example: --rend-drop Thatguy 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_rend_dropper(self, ctx, name, time):
        await add_update_drop_dropper(ctx, rend, name, time)

    @commands.command(name='ony-drop', aliases=generate_dropper_aliases("ony"), help='Sets a ony confirmed dropper with time - example: --ony-drop Thatguy 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_ony_dropper(self, ctx, name, time):
        await add_update_drop_dropper(ctx, ony, name, time)

    @commands.command(name='nef-drop', aliases=generate_dropper_aliases("nef"), help='Sets a nef confirmed dropper with time - example: --nef-drop Thatguy 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_nef_dropper(self, ctx, name, time):
        await add_update_drop_dropper(ctx, nef, name, time)

    @commands.command(name='hakkar-drop', aliases=generate_dropper_aliases("hakkar")+["yi-drop"]+generate_dropper_aliases("yi"), help='Sets a hakkar confirmed dropper with time - example: --hakkar-drop Thatguy 2:54pm')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_hakkar_dropper(self, ctx, name, time):
        if await validate_time_format(time) or await validate_time_format(name):
            await add_update_drop_dropper(ctx, hakkar, name, time)
        else:
            await ctx.send('Invalid time provided, format must be HH:MM[am|pm] - example: {0.prefix}{0.command.name} Thatguy 2:54pm'.format(ctx))


class BuffDropRemoveCommands(commands.Cog, name='Removes a buff dropper with matching <name or time>'):
    @commands.command(name='rend-drop-remove', aliases=['rend-drops-remove'], brief='Remove user dropping rend', help='Removes a rend confirmed dropper - example: --rend-drop-remove Thatguy')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def remove_rend_dropper(self, ctx, name_or_time):
        await remove_buff_dropper(ctx, rend, name_or_time)

    @commands.command(name='ony-drop-remove', aliases=['ony-drops-remove'], brief='Remove user dropping ony', help='Removes a ony confirmed dropper - example: --ony-drop-remove Thatguy')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def remove_ony_dropper(self, ctx, name_or_time):
        await remove_buff_dropper(ctx, ony, name_or_time)

    @commands.command(name='nef-drop-remove', aliases=['nef-drops-remove'], brief='Remove user dropping nef', help='Removes a nef confirmed dropper - example: --nef-drop-remove Thatguy')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def remove_nef_dropper(self, ctx, name_or_time):
        await remove_buff_dropper(ctx, nef, name_or_time)

    @commands.command(name='hakkar-drop-remove', aliases=['hakkar-drops-remove', 'yi-drop-remove', 'yi-drops-remove'], brief='Remove user dropping hakkar', help='Removes a hakkar confirmed dropper - example: --hakkar-drop-remove Thatguy')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def remove_hakkar_dropper(self, ctx, name_or_time):
        await remove_buff_dropper(ctx, hakkar, name_or_time)

class SummonerAddCommands(commands.Cog, name='Adds the <name> of a summoner and the [note] which may contain cost or other info'):
    def generate_summoner_aliases(location):
        return ["{0}-sums-add".format(location), "{0}-summ".format(location), "{0}-summ-add".format(location), "{0}-summs".format(location), "{0}-summs-add".format(location), "{0}-sum".format(location), "{0}-sum-add".format(location)]
        
    @commands.command(name='yi-sums', aliases=generate_summoner_aliases("yi"), help='Adds a YI summoner with cost/message - example: --yi-sums Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def add_hakkar_yi_summons(self, ctx, name, *note):
        await add_update_service_seller(ctx, Services.YI, name, note)

    @commands.command(name='bb-sums', aliases=generate_summoner_aliases("bb"), help='Adds a BB summoner with cost/message - example: --bb-sums Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def add_hakkar_bb_summons(self, ctx, name, *note):
        await add_update_service_seller(ctx, Services.BB, name, note)

    @commands.command(name='bvsf-sums', aliases=generate_summoner_aliases("bvsf"), help='Adds a BVSF summoner with cost/message - example: --bvsf-sums Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def add_bvsf_summons(self, ctx, name, *note):
        await add_update_service_seller(ctx, Services.BVSF, name, note)

    @commands.command(name='dmt-sums', aliases=generate_summoner_aliases("dmt")+["dm-sums"]+generate_summoner_aliases("dm"), help='Adds a DMT summoner with cost/message - example: --dmt-sums Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def add_dmt_summons(self, ctx, name, *note):
        await add_update_service_seller(ctx, Services.DMTS, name, note)

    @commands.command(name='dmf-sums', aliases=generate_summoner_aliases("dmf"), help='Adds a DMF summoner with cost/message - example: --dmf-sums Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def add_dmf_summons(self, ctx, name, *note):
        await add_update_service_seller(ctx, Services.DMF, name, note)

    @commands.command(name='naxx-sums', aliases=generate_summoner_aliases("naxx")+["nax-sums"]+generate_summoner_aliases("nax"), help='Adds a Naxx summoner with cost/message - example: --naxx-sums Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def add_naxx_summons(self, ctx, name, *note):
        await add_update_service_seller(ctx, Services.NAXX, name, note)

    @commands.command(name='aq-sums', aliases=generate_summoner_aliases("aq"), help='Adds a AQ Gates summoner with cost/message - example: --aq-sums Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def add_aq_summons(self, ctx, name, *note):
        await add_update_service_seller(ctx, Services.AQ, name, note)

    @commands.command(name='brm-sums', aliases=generate_summoner_aliases("brm"), help='Adds a BRM summoner with cost/message - example: --brm-sums Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def add_brm_summons(self, ctx, name, *note):
        await add_update_service_seller(ctx, Services.BRM, name, note)

    @commands.command(name='wicker-sums', aliases=generate_summoner_aliases("wicker")+["wickerman-sums"]+generate_summoner_aliases("wickerman"), help='Adds a wickerman (trisifal glades) summoner with cost/message - example: --wicker-sums Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def add_wickerman_summons(self, ctx, name, *note):
        await add_update_service_seller(ctx, Services.WICKERMAN, name, note)


class SummonerRemoveCommands(commands.Cog, name='Removes the <name> of a summoner'):
    def generate_summoner_remove_aliases(location):
        return ["{0}-summ-remove".format(location), "{0}-summs-remove".format(location), "{0}-sum-remove".format(location)]
        
    @commands.command(name='yi-sums-remove', aliases=generate_summoner_remove_aliases("yi"), brief='Remove user that was summoning to YI', help='Removes a YI summoner - example: --yi-sums-remove Thatguy')
    @coordinator_or_seller(seller=True)
    async def remove_hakkar_yi_summons(self, ctx, name):
        await remove_service_seller(ctx, Services.YI, name)

    @commands.command(name='bb-sums-remove', aliases=generate_summoner_remove_aliases("bb"), brief='Remove user that was summoning to BB', help='Removes a BB summoner - example: --bb-sums-remove Thatguy')
    @coordinator_or_seller(seller=True)
    async def remove_hakkar_bb_summons(self, ctx, name):
        await remove_service_seller(ctx, Services.BB, name)

    @commands.command(name='bvsf-sums-remove', aliases=generate_summoner_remove_aliases("bvsf"), brief='Remove user that was summoning to BVSF', help='Removes a BVSF summoner - example: --bvsf-sums-remove Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def remove_bvsf_summons(self, ctx, name):
        await remove_service_seller(ctx, Services.BVSF, name)

    @commands.command(name='dmt-sums-remove', aliases=generate_summoner_remove_aliases("dmt")+["dm-sums-remove"]+generate_summoner_remove_aliases("dm"), brief='Remove user that was summoning to DMT', help='Removes a DMT summoner - example: --dmt-sums-remove Thatguy')
    @coordinator_or_seller(seller=True)
    async def remove_dmt_summons(self, ctx, name):
        await remove_service_seller(ctx, Services.DMTS, name)

    @commands.command(name='dmf-sums-remove', aliases=generate_summoner_remove_aliases("dmf"), brief='Remove user that was summoning to DMF', help='Removes a DMF summoner - example: --dmf-sums-remove Thatguy')
    @coordinator_or_seller(seller=True)
    async def remove_dmf_summons(self, ctx, name):
        await remove_service_seller(ctx, Services.DMF, name)

    @commands.command(name='naxx-sums-remove', aliases=generate_summoner_remove_aliases("naxx")+["nax-sums-remove"]+generate_summoner_remove_aliases("nax"), brief='Remove user that was summoning to Naxx', help='Removes a Naxx summoner - example: !naxx-sums-remove Thatguy')
    @coordinator_or_seller(seller=True)
    async def remove_naxx_summons(self, ctx, name):
        await remove_service_seller(ctx, Services.NAXX, name)

    @commands.command(name='aq-sums-remove', aliases=generate_summoner_remove_aliases("aq"), brief='Remove user that was summoning to AQ Gates', help='Removes a AQ Gates summoner - example: --aq-sums-remove Thatguy')
    @coordinator_or_seller(seller=True)
    async def remove_aq_summons(self, ctx, name):
        await remove_service_seller(ctx, Services.AQ, name)

    @commands.command(name='brm-sums-remove', aliases=generate_summoner_remove_aliases("brm"), brief='Remove user that was summoning to BRM', help='Removes a BRM summoner - example: --brm-sums-remove Thatguy')
    @coordinator_or_seller(seller=True)
    async def remove_brm_summons(self, ctx, name):
        await remove_service_seller(ctx, Services.BRM, name)

    @commands.command(name='wicker-sums-remove', aliases=generate_summoner_remove_aliases("wicker")+["wickerman-sums-remove"]+generate_summoner_remove_aliases("wickerman"), brief='Remove user that was summoning to Wickerman', help='Removes a Wickerman summoner - example: --wicker-sums-remove Thatguy')
    @coordinator_or_seller(seller=True)
    async def remove_wickerman_summons(self, ctx, name):
        await remove_service_seller(ctx, Services.WICKERMAN, name)


class DMTBuffCommands(commands.Cog, name = 'Adds the <name> of a DMT buff seller and the [note] which may contain cost or other info or Removes the <name> of the DMT buffer'):
    @commands.command(name='dmt-buffs', aliases=['dmt-buffs-add', 'dmt-buff', 'dmt-buff-add', 'dm-buffs', 'dm-buffs-add', 'dm-buff', 'dm-buff-add'], help='Adds a DMT buffer with cost/message - example: --dmt-buffs Thatguy 5g w/port')
    @coordinator_or_seller(seller=True)
    async def add_dmt_buffs(self, ctx, name, *note):
        await add_update_service_seller(ctx, Services.DMTB, name, note)

    @commands.command(name='dmt-buffs-remove', aliases=['dmt-buff-remove', 'dm-buffs-remove', 'dm-buff-remove'], help='Removes a DMT buffer - example: --dmt-buffs-remove Thatguy')
    @coordinator_or_seller(seller=True)
    async def remove_dmt_buffs(self, ctx, name):
        await remove_service_seller(ctx, Services.DMTB, name)


class DMFBuffCommands(commands.Cog, name = 'Specifies the [location] of the DMF (Elwynn Forest or Mulgore) - specifying no location will hide the message when no summoners are present'):
    @commands.command(name='dmf-loc', brief='Sets the location of the DMF', help='Sets the location of the DMF - example: --dmf-loc Elwynn Forest')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_dmf_location(self, ctx, *location):
        global dmf_location
        dmf_location = (await construct_args_message(location)).title()
        await post_in_world_buffs_chat_channel()
        if len(dmf_location) > 0 or len(sellers.sellers[Services.DMF]) > 0:
            await playback_message(ctx, 'DMF buff timer updated to:\n' + await calc_dmf_msg())
        else:
            await playback_message(ctx, 'DMF buff timer removed')


class ServerMaintenanceCommands(commands.Cog, name = 'Specifies the maintenance or server status [message] - specifying no message will hide the message'):
    @commands.command(name='server-status', brief='Set a message to display in the server status section', help='Sets a message to display in the server status section - example: --server-status server restart @10:00am')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_maintenance_message(self, ctx, *message):
        global server_maintenance
        server_maintenance = await construct_args_message(message)
        await post_in_world_buffs_chat_channel()
        if len(server_maintenance) > 0:
            await playback_message(ctx, 'Server status message updated to:\n' + await get_maintenance())
        else:
            await playback_message(ctx, 'Server status message removed')


class GriefingCommands(commands.Cog, name = 'Specifies the ally sighting / griefing [message] - specifying no message will hide the message'):
    @commands.command(name='ally', brief='Set a message to display in the ally warning section', help='Sets a message to display in the ally warning section - example: --ally Ally sighting at BRM')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_alliance_message(self, ctx, *message):
        global alliance
        alliance = await construct_args_message(message)
        await post_in_world_buffs_chat_channel()
        if len(alliance) > 0:
            await playback_message(ctx, 'Alliance warning message updated to:\n' + await get_alliance())
        else:
            await playback_message(ctx, 'Alliance warning message removed')
            
    @commands.command(name='ally-remove', brief='Clears the ally message', help='Clears the ally section and hides it - example: --ally-remove')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def clear_alliance_message(self, ctx):
        global alliance
        alliance = ''
        await post_in_world_buffs_chat_channel()
        await playback_message(ctx, 'Alliance warning message removed')


class ExtraMessageCommands(commands.Cog, name = 'Specifies an additional footer [message] - specifying no message will hide the message'):
    @commands.command(name='extra-msg', brief='Set a message to display in the extra message/footer section', help='Sets a message to display in the extra message/footer section - example: --extra-msg Ally sighting at BRM')
    @commands.has_role(WORLD_BUFF_COORDINATOR_ROLE_ID)
    async def set_extra_footer_message(self, ctx, *message):
        global extra_message
        extra_message = await construct_args_message(message)
        await post_in_world_buffs_chat_channel()
        if len(extra_message) > 0:
            await playback_message(ctx, 'Extra footer message updated to:\n' + await get_extra_message())
        else:
            await playback_message(ctx, 'Extra footer message removed')

@bot.command(name='dendave-add', description='Sets the extra message/footer section with the Dendave seller message - example: --dendave-add')
@coordinator_or_seller(seller=True)
async def set_dendave_extra_footer_message(ctx):
    global extra_message
    extra_message = ":airplane::heartpulse::wilted_rose::crown::bug::mountain: **Denmule** selling 8g summons to all raid & buff locations. Whisper 'inv __' with destination (i.e. Blasted Lands, DMT, BVSF, YI, AQ, BWL, MC, Org)"
    await post_in_world_buffs_chat_channel()
    await playback_message(ctx, 'Extra footer message updated to:\n' + await get_extra_message())
    await post_update_in_wbc_channel(ctx, 'Added Dendave extra footer message')

@bot.command(name='dendave-remove', description='Removes the extra message/footer section - example: --dendave-remove')
@coordinator_or_seller(seller=True)
async def remove_dendave_extra_footer_message(ctx):
    global extra_message
    extra_message = ''
    await post_in_world_buffs_chat_channel()
    await playback_message(ctx, 'Extra footer message removed')
    await post_update_in_wbc_channel(ctx, 'Removed Dendave extra footer message')


async def get_buff_times():
    await check_for_bvsf_updates()
    message = await get_timestamp()
    message += await get_maintenance()
    message += await calc_rend_msg() + '\n'
    message += await calc_ony_msg() + '\n'
    message += await calc_nef_msg() + '\n'
    message += await calc_hakkar_msg() + '\n'
    message += await calc_bvsf_msg() + '\n'
    message += await calc_dmt_msg() + '\n'
    message += await calc_naxx_msg()
    message += await calc_aq_msg()
    message += await calc_brm_msg()
    message += await calc_dmf_msg()
    message += await calc_wicker_msg()
    message += await get_alliance()
    message += await get_extra_message()
    return message

async def get_timestamp():
    local_time = await get_local_time()
    return '**Updated as of ' + datetime.strftime(local_time, '%Y-%m-%d at ' + PRINT_TIME_FORMAT).lower() + ' ST**\n\n'

async def get_maintenance():
    if len(server_maintenance) > 0:
        return ':tools: **' + server_maintenance + '** :tools:\n\n'
    else:
        return ''

async def get_alliance():
    if len(alliance) > 0:
        return ':warning:  ' + alliance + '\n'
    else:
        return ''

async def get_extra_message():
    if len(extra_message) > 0:
        return '\n' + extra_message + '\n'
    else:
        return ''

async def calc_rend_msg():
    message = ':japanese_ogre:  Rend --- ' + rend.time
    message += await droppers_msg(rend)
    return message

async def calc_ony_msg():
    message = ':dragon:  Ony --- ' + ony.time
    message += await droppers_msg(ony)
    return message

async def calc_nef_msg():
    message = ':dragon_face:  Nef --- ' + nef.time
    message += await droppers_msg(nef)
    return message

async def calc_hakkar_msg():
    message = ':heartpulse:  Hakkar --- '
    if len(hakkar.drops) > 0:
        droppers = ''
        for drop in hakkar.drops:
            if len(droppers) > 0:
                droppers += ',  '
            droppers += drop.time + ' (**' + drop.name + '**)'
        message += droppers
    else:
        message += TIME_UNKNOWN
    if len(sellers.sellers[Services.YI]) > 0:
        message += '  --  ' + await summoners_buffers_msg(sellers.sellers[Services.YI], 'YI summons')
    if len(sellers.sellers[Services.BB]) > 0:
        message += '  --  ' + await summoners_buffers_msg(sellers.sellers[Services.BB], 'BB summons')
    return message

async def calc_bvsf_msg():
    if await validate_time_format(bvsf_time):
        next_time_1 = await calculate_next_time(bvsf_time, 25)
        next_time_2 = await calculate_next_time(next_time_1, 25)
        message = ':wilted_rose:  BVSF --- ' + bvsf_time + ' -> ' + next_time_1 + ' -> ' + next_time_2
    else:
        message = ':wilted_rose:  BVSF --- ' + bvsf_time
    if len(sellers.sellers[Services.BVSF]) > 0:
        message += '  --  ' + await summoners_buffers_msg(sellers.sellers[Services.BVSF])
    return message

async def calc_dmt_msg():
    message = await summoners_buffers_msg(sellers.sellers[Services.DMTB], 'DM buffs')
    if len(message) == 0:
        message = 'No buffs available at this time'
    if len(sellers.sellers[Services.DMTS]) > 0:
        if len(message) > 0:
            message += '  --  ' + await summoners_buffers_msg(sellers.sellers[Services.DMTS])
        else:
            message = await summoners_buffers_msg(sellers.sellers[Services.DMTS])
    message = ':crown:  DMT --- ' + message
    return message

async def calc_naxx_msg():
    message = ''
    if len(sellers.sellers[Services.NAXX]) > 0:
        message = ':skull:  Naxx --- ' + await summoners_buffers_msg(sellers.sellers[Services.NAXX]) + '\n'
    return message

async def calc_aq_msg():
    message = ''
    if len(sellers.sellers[Services.AQ]) > 0:
        message = ':bug:  AQ Gates --- ' + await summoners_buffers_msg(sellers.sellers[Services.AQ]) + '\n'
    return message

async def calc_brm_msg():
    message = ''
    if len(sellers.sellers[Services.BRM]) > 0:
        message = ':mountain:  BRM --- ' + await summoners_buffers_msg(sellers.sellers[Services.BRM]) + '\n'
    return message

async def calc_dmf_msg():
    if len(dmf_location) == 0 and len(sellers.sellers[Services.DMF]) == 0:
        return ''
    message = ''
    if len(dmf_location) > 0:
        message = ':circus_tent:  DMF (' + dmf_location + ') --- '
    else:
        message = ':circus_tent:  DMF --- '
    if len(sellers.sellers[Services.DMF]) > 0:
        message += await summoners_buffers_msg(sellers.sellers[Services.DMF])
    else:
        message += ' No summons available at this time'
    message += '\n'
    return message

async def calc_wicker_msg():
    message = ':jack_o_lantern:  Wickerman (Tirisfal Glades) --- '
    if len(sellers.sellers[Services.WICKERMAN]) > 0:
        message += await summoners_buffers_msg(sellers.sellers[Services.WICKERMAN])
    else:
        message += ' No summons available at this time'
    message += '\n'
    return message

async def check_for_bvsf_updates():
    global bvsf_time
    global bvsf_update_count
    if not await validate_time_format(bvsf_time):
        return False;
    local_time = await get_local_time()
    bvsf_date_time = datetime.strptime(bvsf_time, '%I:%M%p')
    new_time = local_time.replace(hour=bvsf_date_time.hour, minute=bvsf_date_time.minute)
    if local_time > new_time and (local_time.hour < 23 or bvsf_date_time.hour > 1):
        new_time += timedelta(minutes=25)
        bvsf_time = datetime.strftime(new_time, PRINT_TIME_FORMAT).lower()
        bvsf_update_count += 1
        return True
    else:
        return False

async def calc_minutes_since_time(time):
    if not await validate_time_format(time):
        return -1
    local_time = await get_local_time()
    date_time = datetime.strptime(time, '%I:%M%p')
    new_time = local_time.replace(hour=date_time.hour, minute=date_time.minute)
    minutes = (local_time - new_time).total_seconds() / 60
    if 30 > minutes > 0:
        return minutes
    return -1

async def time_is_open(time):
    return True if 'open' in time.lower() else False


async def get_local_time():
    utc = timezone('UTC')
    now = utc.localize(datetime.utcnow())
    local_time = now.astimezone(timezone('US/Eastern'))
    return local_time

async def droppers_msg(drop_buffs):
    message = ''
    for drop in drop_buffs.drops:
        if len(message) > 0:
            message += ', '
        if drop.time == drop_buffs.time:
            message += ' (**' + drop.name + '**)'
        else:
            message += ' (' + drop.time + ' - **' + drop.name + '**)'
    return message

async def summoners_buffers_msg(summoners, message_ending = 'summons'):
    message = ''
    if len(summoners) > 0:
        message += 'Whisper '
        for index in range(len(summoners)):
            summoner = summoners[index]
            if index > 0:
                message += '  |  '
            message += ' **' + summoner.name + '** '
            if len(summoner.msg) > 0:
                message += '(' + summoner.msg + ') '
        message += ' \'inv\' for {0}'.format(message_ending)
    return message

async def format_time(time):
    time = await correct_time_format(time)
    if not await validate_time_format(time):
        return time;
    date_time = datetime.strptime(time, '%I:%M%p')
    return datetime.strftime(date_time, PRINT_TIME_FORMAT).lower()

async def post_update_in_wbc_channel(ctx, embed_desc, name=None, note=None, header="**DM Update**"):
    if (ctx.message.guild == None):
        wbc_channel = bot.get_channel(WBC_CHANNEL_ID)
        embed = discord.Embed(title=header, description=embed_desc, color=0xa6a6a6)
        embed.add_field(name="Author", value=ctx.message.author.mention, inline=False)
        if name != None:
            embed.add_field(name="Character Name", value=name.title(), inline=True)
        if note != None:
            note_str = await construct_args_message(note)
            if note_str == '':
                note_str = '*No message applied*'
            embed.add_field(name="Note/Message", value=note_str, inline=True)
        await wbc_channel.send(embed=embed)

def remove_command_surrounding_special_characters(text):
    if (text.startswith('<') and text.endswith('>')) or (text.startswith('[') and text.endswith(']')):
        return text[1:-1]
    else:
        return text

async def construct_args_message(args):
    message = ''
    for index in range(len(args)):
        if index > 0:
            message = message + ' '
        message += args[index]
    message = remove_command_surrounding_special_characters(message)
    return message

async def calculate_next_time(time_str, minutes_to_add):
    if not await validate_time_format(time_str):
        return;
    time = datetime.strptime(time_str, '%I:%M%p')
    new_time = time + timedelta(minutes=minutes_to_add)
    return datetime.strftime(new_time, PRINT_TIME_FORMAT).lower()

async def validate_time_format(time):
    valid = re.search('^[0-1]?[0-9]:[0-5][0-9][a,p]m$', time.lower())
    return valid

async def correct_time_format(time):
    is_time_without_am_pm = re.search('^[0-1]?[0-9]:[0-5][0-9]$', time.lower())
    if is_time_without_am_pm:
        utc = timezone('UTC')
        now = utc.localize(datetime.utcnow())
        local_time = now.astimezone(timezone('US/Eastern'))
        current_hour = local_time.hour
        time_hour = int(time.split(":")[0])
        # change time to 0 for midnight/noon
        if time_hour == 12:
            time_hour = 0
        # 12-23 -> currently pm
        if (current_hour > 11):
            current_hour = current_hour - 12
            # 17 -> 5 > 1 --- set to am
            if (current_hour > time_hour):
                return time+"am"
            # 17 -> 5 < 8 --- set to pm
            else:
                return time+"pm"
        # 0-11 -> currently am
        else:
            # 5 > 1 --- set to pm
            if (current_hour > time_hour):
                return time+"pm"
            # 5 < 8 --- set to am
            else:
                return time+"am"
    return time

async def playback_message(ctx, message):
    if (playback_updates):
        await ctx.send(message)

async def post_in_world_buffs_chat_channel():
    try:
        await update_world_buffs_chat_channel()
    except:
        # just try to update again...
        await update_world_buffs_chat_channel()

async def update_world_buffs_chat_channel():
    channel = bot.get_channel(WORLD_BUFF_CHANNEL_ID)
    messages = await channel.history(limit = 1).flatten()
    if len(messages) > 0 and messages[0].author == bot.user:
        message = await channel.fetch_message(messages[0].id)
        await message.edit(content = await get_buff_times())
    else:
        await channel.send(await get_buff_times())

# used to sort drops by time
def sort_by_time(dropper):
    utc = timezone('UTC')
    now = utc.localize(datetime.utcnow())
    local_time = now.astimezone(timezone('US/Eastern'))
    if re.search('^[0-1]?[0-9]:[0-5][0-9][a,p]m$', dropper.time):
        date_time = datetime.strptime(dropper.time, '%I:%M%p')
        new_time = local_time.replace(hour=date_time.hour, minute=date_time.minute)
        minutes = (local_time - new_time).total_seconds() / 60
        if minutes > 60:
            new_time += timedelta(days=1)
        return new_time
    else:
        return local_time


# Sample Message to process
#Updated as of 2020-09-11 at 07:42am ST

#:tools: **SERVER IS UP** :tools:

#:japanese_ogre:  Rend --- 8:00am (8:05am - **Dajokerrrend**) (9:05am - **Norend**)
#:dragon:  Ony --- 8:05am (**Dajokerrrend**)
#:dragon_face:  Nef --- 9:09am (9:10am - **Dajokerrnef**)
#:heartpulse:  Hakkar --- 4:45pm (**Test**),  5:45pm (**Tester**)  --  Whisper  **Yisums** (1g)  'inv' for YI summons  --  Whisper  **Bbsums** (2g)  'inv' for BB summons
#:wilted_rose:  BVSF --- 5:10pm -> 5:35pm -> 6:00pm  --  Whisper  **Bvsfsums** (5g)  'inv' for summons
#:crown:  DMT --- Whisper  **Buffer** (5g)   |   **Betterbuffer** (10g w/summon + port)  'inv' for DM buffs  --  Whisper  **Dmtsums** (3g)  'inv' for summons
#:skull:  Naxx --- Whisper  **Naxxsum** (7g)  'inv' for summons
#:bug:  AQ Gates --- Whisper  **Aqsum** (7g)  'inv' for summons
#:mountain:  BRM --- Whisper  **Brmsums** (5g or 10g w/FR :fire_extinguisher:)  'inv' for summons
#:circus_tent:  DMF (Elwynn Forest) --- Whisper  **Dmfsums** (4g w/port)  'inv' for summons
#:warning:  ALLY ALL OVER

#:airplane: :heartpulse::wilted_rose::crown::bug: :mountain: Denmule selling 8g summons to all raid & buff locations. Whisper 'inv __' with destination (i.e. DMT, BVSF, YI, AQ, BWL, MC, Org, ZG)
async def populate_data_from_message(message):
    populate_success = True
    lines = message.split("\n")
    for index in range(len(lines)):
        line = lines[index]
        if line.startswith(':tools:'):
            #:tools: SERVER IS UP :tools:
            global server_maintenance
            strings = line.split(':tools:')
            non_bold_strings = strings[1].split('**')
            server_maintenance = remove_command_surrounding_special_characters(non_bold_strings[1])
            if await get_maintenance() != line + '\n\n':
                populate_success = False
                print('server_status')
        elif line.startswith(':japanese_ogre:  Rend --- '):
            #:japanese_ogre:  Rend --- 8:00am (8:05am - **Dajokerrrend**) (9:05am - **Norend**)
            global rend
            strings = line.split(':japanese_ogre:  Rend --- ')
            parts = strings[1].split('(')
            rend.time = remove_command_surrounding_special_characters(parts[0].strip())
            await process_droppers(rend, parts[1:], rend.time)
            if await calc_rend_msg() != line:
                populate_success = False
                print('rend')
        elif line.startswith(':dragon:  Ony --- '):
            #:dragon:  Ony --- 8:05am (**Dajokerrrend**)
            global ony
            strings = line.split(':dragon:  Ony --- ')
            parts = strings[1].split('(')
            ony.time = remove_command_surrounding_special_characters(parts[0].strip())
            await process_droppers(ony, parts[1:], ony.time)
            if await calc_ony_msg() != line:
                populate_success = False
                print('ony')
        elif line.startswith(':dragon_face:  Nef --- '):
            #:dragon_face:  Nef --- 9:09am (9:10am - **Dajokerrnef**)
            global nef
            strings = line.split(':dragon_face:  Nef --- ')
            parts = strings[1].split('(')
            nef.time = remove_command_surrounding_special_characters(parts[0].strip())
            await process_droppers(nef, parts[1:], nef.time)
            if await calc_nef_msg() != line:
                populate_success = False
                print('nef')
        elif line.startswith(':heartpulse:  Hakkar --- '):
            #:heartpulse:  Hakkar --- 4:45pm (**Test**),  5:45pm (**Tester**)  --  Whisper  **Yisums** (1g)  'inv' for YI summons  --  Whisper  **Bbsums** (2g)  'inv' for BB summons
            strings = line.split(':heartpulse:  Hakkar --- ')
            parts = strings[1].split('  --  ')
            if parts[0] != TIME_UNKNOWN:
                drops = parts[0].split(',')
                for drop in drops:
                    drop_parts = drop.split(' (')
                    drop_name = drop_parts[1].split('**')
                    hakkar.add_drop(drop_parts[0].strip(), drop_name[1])
            for summon_zone in parts[1:]:
                if 'YI summons' in summon_zone:
                    await process_summoners_buffers(Services.YI, summon_zone)
                elif 'BB summons' in summon_zone:
                    await process_summoners_buffers(Services.BB, summon_zone)
            if await calc_hakkar_msg() != line:
                populate_success = False
                print('hakkar')
        elif line.startswith(':wilted_rose:  BVSF --- '):
            #:wilted_rose:  BVSF --- 5:10pm -> 5:35pm -> 6:00pm  --  Whisper  **Bvsfsums** (5g)  'inv' for summons
            global bvsf_time
            strings = line.split(':wilted_rose:  BVSF --- ')
            parts = strings[1].split('  --  ')
            timer = parts[0].split(' ->')
            bvsf_time = timer[0]
            if len(parts) > 1:
                await process_summoners_buffers(Services.BVSF, parts[1])
            if await calc_bvsf_msg() != line:
                populate_success = False
                print('bvsf')
        elif line.startswith(':crown:  DMT --- '):
            #:crown:  DMT --- Whisper  **Buffer** (5g)   |   **Betterbuffer** (10g w/summon + port)  'inv' for DM buffs  --  Whisper  **Dmtsums** (3g)  'inv' for summons
            strings = line.split(':crown:  DMT --- ')
            parts = strings[1].split('  --  ')
            for type in parts:
                if 'DM buffs' in type:
                    await process_summoners_buffers(Services.DMTB, type)
                elif 'for summons' in type:
                    await process_summoners_buffers(Services.DMTS, type)
            if await calc_dmt_msg() != line:
                populate_success = False
                print('dmt')
        elif line.startswith(':skull:  Naxx --- '):
            #:skull:  Naxx --- Whisper  **Naxxsum** (7g)  'inv' for summons
            strings = line.split(':skull:  Naxx --- ')
            if 'for summons' in strings[1]:
                await process_summoners_buffers(Services.NAXX, strings[1])
            if await calc_naxx_msg() != line + '\n':
                populate_success = False
                print('naxx')
        elif line.startswith(':bug:  AQ Gates --- '):
            #:bug:  AQ Gates --- Whisper  **Aqsum** (7g)  'inv' for summons
            strings = line.split(':bug:  AQ Gates --- ')
            if 'for summons' in strings[1]:
                await process_summoners_buffers(Services.AQ, strings[1])
            if await calc_aq_msg() != line + '\n':
                populate_success = False
                print('aq')
        elif line.startswith(':mountain:  BRM --- '):
            #:mountain:  BRM --- Whisper  **Brmsums** (5g or 10g w/FR :fire_extinguisher:)  'inv' for summons
            strings = line.split(':mountain:  BRM --- ')
            if 'for summons' in strings[1]:
                await process_summoners_buffers(Services.BRM, strings[1])
            if await calc_brm_msg() != line + '\n':
                populate_success = False
                print('brm')
        elif line.startswith(':circus_tent:  DMF '):
            #:circus_tent:  DMF (Elwynn Forest) --- Whisper  **Dmfsums** (4g w/port)  'inv' for summons
            global dmf_location
            strings = line.split(' --- ')
            if '(' in strings[0]:
                dmf_location = strings[0].split('(')[1].split(')')[0]
            if 'for summons' in strings[1]:
                await process_summoners_buffers(Services.DMF, strings[1])
            if await calc_dmf_msg() != line + '\n':
                populate_success = False
                print('dmf')
        elif line.startswith(':jack_o_lantern:  Wickerman (Tirisfal Glades) --- '):
            #:jack_o_lantern:  Wickerman (Tirisfal Glades) --- Whisper  **Brmsums** (5g)  'inv' for summons
            strings = line.split(':jack_o_lantern:  Wickerman (Tirisfal Glades) --- ')
            if 'for summons' in strings[1]:
                await process_summoners_buffers(Services.WICKERMAN, strings[1])
            if await calc_wicker_msg() != line + '\n':
                populate_success = False
                print('wickerman')
        elif line.startswith(':warning:'):
            #:warning:  ALLY ALL OVER
            global alliance
            strings = line.split(':warning:')
            alliance = remove_command_surrounding_special_characters(strings[1].strip())
            if await get_alliance() != line + '\n':
                populate_success = False
                print('ally')
        elif index == len(lines) - 1:
            #:airplane: :heartpulse::wilted_rose::crown::bug: :mountain: Denmule selling 8g summons to all raid & buff locations. Whisper 'inv __' with destination (i.e. DMT, BVSF, YI, AQ, BWL, MC, Org, ZG)
            global extra_message
            if line != '':
                extra_message = remove_command_surrounding_special_characters(line)
                if await get_extra_message() != '\n' + line + '\n':
                    populate_success = False
                    print('extra_message')
    return populate_success

async def process_droppers(buff, droppers_raw, drop_time):
    for drop in droppers_raw:
        if ' - ' in drop:
            drop_split = drop.split(' - ')
            buff.add_drop(drop_split[0], drop_split[1].split('**')[1])
        else:
            buff.add_drop(drop_time, drop.split('**')[1])

async def process_summoners_buffers(service, message):
    summoners_buffers_raw = message.split(' | ')
    for summoner_buffer in summoners_buffers_raw:
        parts = summoner_buffer.split('**')
        summoner_note = ''
        if '(' in parts[2] and ')' in parts[2]:
            index_start = parts[2].index('(') + 1
            index_end = parts[2].rindex(')')
            summoner_note = parts[2][index_start:index_end]
        sellers.add_seller(service, parts[1], summoner_note)

# clear all stored data
async def clear_all_data():
    global server_maintenance
    server_maintenance = ''
    rend.clear()
    ony.clear()
    nef.clear()
    hakkar.clear()
    global sellers
    sellers = Sellers()
    global bvsf_time
    bvsf_time = TIME_UNKNOWN
    global bvsf_update_count
    bvsf_update_count = 0
    global dmf_location
    dmf_location = ''
    global alliance
    alliance = ''
    global extra_message
    extra_message = ''

# debug ouput for testing/verification
async def debug_print_services():
    if DEBUG:
        for service in Services:
            print("{0}={1}".format(service, sellers.sellers[service]))
        sys.stdout.flush()

# debug ouput for testing/verification
async def debug_print_drop_buffs(buff):
    if DEBUG:
        print(buff)
        sys.stdout.flush()


# class for rend/ony/nef buff times and droppers
class DropBuffs:
    def __init__(self, n='', o=None):
        self.name = n
        self.time = TIME_UNKNOWN
        self.drops = []
        self.output_function = o
    
    def find_dropper(self, name_or_time):
        # fix any formatting issues and do .lower for comparison
        clean_name_or_time = remove_command_surrounding_special_characters(name_or_time).lower()
        for dropper in self.drops:
            # try to find a matching dropper via name or time
            if dropper.name.lower() == clean_name_or_time or dropper.time.lower() == clean_name_or_time:
                return dropper
        # if no match found, just return None
        return None

    def add_drop(self, time, name, author_id=''):
        self.drops.append(Dropper(time, name, author_id))

    def sort_drops(self):
        self.drops.sort(key=sort_by_time)

    def remove_drop(self, dropper):
        self.drops.remove(dropper)

    def clear(self):
        self.time = TIME_UNKNOWN
        self.drops = []
        
    def __repr__(self):
        return "Buff:{0}---Time:{1}---Drops:{2}".format(self.name, self.time, self.drops)

# class for dropper info
class Dropper:
    def __init__(self, t=TIME_UNKNOWN, n='NA', a=''):
        self.time = t
        self.name = n
        self.author = a

    def __repr__(self):
        return "Time:{0}---Name:{1}---AuthorID:{2}".format(self.time, self.name, self.author)

class ServiceInfo:
    def __init__(self, n, i, s, o, f):
        self.name = n
        self.icon = i
        self.summoner = s
        self.output_line_name = o
        self.output_function = f

# enum class for all possible summon/buff services sold
class Services(enum.Enum):
    YI = ServiceInfo("YI", ":heartpulse:", True, "Hakkar", calc_hakkar_msg)
    BB = ServiceInfo("BB", ":heartpulse:", True, "Hakkar", calc_hakkar_msg)
    BVSF = ServiceInfo("BVSF", ":wilted_rose:", True, "BVSF", calc_bvsf_msg)
    DMTB = ServiceInfo("DMT", ":crown:", False, "DMT", calc_dmt_msg)
    DMTS = ServiceInfo("DMT", ":crown:", True, "DMT", calc_dmt_msg)
    DMF = ServiceInfo("DMF", ":circus_tent:", True, "DMF", calc_dmf_msg)
    BRM = ServiceInfo("BRM", ":mountain:", True, "BRM", calc_brm_msg)
    AQ = ServiceInfo("AQ", ":bug:", True, "AQ", calc_aq_msg)
    NAXX = ServiceInfo("NAXX", ":skull:", True, "Naxx", calc_naxx_msg)
    WICKERMAN = ServiceInfo("WICKERMAN", ":jack_o_lantern:", True, "Wickerman", calc_wicker_msg)

# class for summons and (DMT) buff sellers
class Sellers:
    def __init__(self):
        # initialize the sellers map
        self.sellers = {new_list: [] for new_list in Services} 

    def find_seller(self, service, name):
        # fix any formatting issues and do .title for comparison
        clean_title_name = remove_command_surrounding_special_characters(name).title()
        for seller in self.sellers[service]:
            # try to find a matching seller via name
            if seller.name.title() == clean_title_name:
                return seller
        # if no match found, just return None
        return None

    def add_seller(self, service, name, message='', author_id=''):
        self.sellers[service].append(SummonerBuffer(name, message, author_id))

    def remove_seller(self, service, seller):
        self.sellers[service].remove(seller)

    def clear_service(self, service):
        self.sellers[service] = []

# class for seller info
class SummonerBuffer:
    def __init__(self, n=TIME_UNKNOWN, m='NA', a=''):
        self.name = n
        self.msg = m
        self.author = a

    def __repr__(self):
        return "Name:{0}---Message:{1}---AuthorID:{2}".format(self.name, self.msg, self.author)

# variables to store the state of all droppers/sellers/etc...
data_loaded = False
playback_updates = True
server_maintenance = ''
rend = DropBuffs(n='Rend', o=calc_rend_msg)
ony = DropBuffs(n='Ony', o=calc_ony_msg)
nef = DropBuffs(n='Nef', o=calc_nef_msg)
hakkar = DropBuffs(n='Hakkar', o=calc_hakkar_msg)
sellers = Sellers()
bvsf_time = TIME_UNKNOWN
bvsf_update_count = 0
dmf_location = ''
alliance = ''
extra_message = ''


# register all cog commands with the bot
bot.add_cog(BuffAvailTimeCommands(bot))
bot.add_cog(BVSFBuffCommands(bot))
bot.add_cog(BuffDropAddCommands(bot))
bot.add_cog(BuffDropRemoveCommands(bot))
bot.add_cog(SummonerAddCommands(bot))
bot.add_cog(SummonerRemoveCommands(bot))
bot.add_cog(DMTBuffCommands(bot))
bot.add_cog(DMFBuffCommands(bot))
bot.add_cog(ServerMaintenanceCommands(bot))
bot.add_cog(GriefingCommands(bot))
bot.add_cog(ExtraMessageCommands(bot))

# run the bot!!
bot.run(TOKEN)
