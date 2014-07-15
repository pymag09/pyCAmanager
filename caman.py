#!/usr/bin/env python3

__author__ = 'Bieliaievskyi Sergey'
__credits__ = ["Bieliaievskyi Sergey"]
__license__ = "Apache License"
__version__ = "1.0.0"
__maintainer__ = "Bieliaievskyi Sergey"
__email__ = "magelan09@gmail.com"
__status__ = "Release"

import curses
import curses.panel
import itertools
import os
import subprocess
import sys


def init_curses():
    my_screen = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    curses.curs_set(0)
    my_screen.keypad(1)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLUE)
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(6, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(7, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    return my_screen


def shutdown_curses(scr_id):
    curses.nocbreak()
    curses.echo()
    scr_id.keypad(0)
    curses.curs_set(1)
    curses.endwin()


def create_main_window(screen_id, height, width):
    def show_win(win_id):
        win_id.bkgd(' ', curses.color_pair(3))
        win_id.clear()
        win_id.box()

    screen_id.addstr(0, 0, ' ' * width, curses.color_pair(3))
    screen_id.addstr(0, 3, 'CA manager', curses.color_pair(3) | curses.A_BOLD)
    left_scr = curses.newwin(height - 4, int(width / 2) - 1, 1, 0)
    left_panel = curses.panel.new_panel(left_scr)
    right_scr = curses.newwin(height - 4, int(width / 2) + 2, 1, int(width / 2) - 1)
    right_panel = curses.panel.new_panel(right_scr)
    show_win(left_scr)
    show_win(right_scr)
    curses.panel.update_panels()
    return (left_scr, left_panel), (right_scr, right_panel)


def get_lines_from_index(page, lines_per_page, filterit=None):
    def get_expiration_date(cn):
        try:
            cert = open(os.environ['PKI_ROOT'] + '/Certs/' + cn + '_cert.pem')
            lines = cert.readlines()
            date = [l for l in lines if 'Not After' in l][0].split('Not After :')[1]
            cert.close()
        except IOError:
            return ''
        return date.rstrip()

    def pars_subj():
        return {element.split('=')[0]: element.split('=')[1] for element in splited_info[5].split('/') if element}

    pure_index_slice = []
    with open('%s%s' % (os.environ['PKI_ROOT'], '/index.txt')) as fd:
        start_line = page * lines_per_page + 1
        iter_index_slice = itertools.islice(fd, start_line, start_line + lines_per_page)
        for line in iter_index_slice:
            splited_info = line.rstrip().split('\t')
            cert_unit_dict = {'Status': splited_info[0],
                              'cert_file_name': splited_info[3],
                              'findit': filterit}
            cert_unit_dict.update(pars_subj())
            cert_unit_dict['expire'] = get_expiration_date(cert_unit_dict['CN'])
            if filterit and filterit[1] not in cert_unit_dict.get(filterit[0], ''):
                continue
            pure_index_slice.append(cert_unit_dict)
    return pure_index_slice


def show_lines(left_panel, right_panel, page=0, max_lines=0, findit=None):
    def fill_panel(panel, info):
        for y, line in enumerate(info):
            ready_line = '%s  %-*s %-*s %s' % (line['Status'],
                                               second_colom_width,
                                               line['CN'],
                                               third_colom_width,
                                               line.get('emailAddress', ''),
                                               line.get('expire', ''))
            panel.addstr(1 + y, 2, ready_line, curses.color_pair(3))
            if findit:
                panel.addstr(1 + y, 2 + ready_line.find(findit[1]), findit[1], curses.color_pair(4) | curses.A_BOLD)
                line['findit_position'] = 2 + ready_line.find(findit[1])
            line['screen'] = panel
            line['y'] = 1 + y
        panel.refresh()

    curses.curs_set(0)
    cert_list = get_lines_from_index(page, max_lines * 2, findit)
    if cert_list:
        second_colom_width = len(max([cn['CN'] for cn in cert_list], key=len)) + 2
        third_colom_width = len(max([email.get('emailAddress', '') for email in cert_list], key=len)) + 2
    left_panel.clear()
    left_panel.box()
    fill_panel(left_panel, cert_list[:max_lines])
    right_panel.clear()
    right_panel.box()
    fill_panel(right_panel, cert_list[max_lines:])
    return cert_list


def keyborad_processor(main_screen):
    def clear_cursor():
        visible_lines[cursor_position]['screen'].chgat(visible_lines[cursor_position]['y'],
                                                       1,
                                                       int(width / 2) - 3,
                                                       curses.color_pair(3))
        if visible_lines[cursor_position]['findit']:
            visible_lines[cursor_position]['screen'].addstr(visible_lines[cursor_position]['y'],
                                                            visible_lines[cursor_position]['findit_position'],
                                                            visible_lines[cursor_position]['findit'][1],
                                                            curses.color_pair(4) | curses.A_BOLD)
        visible_lines[cursor_position]['screen'].refresh()

    def draw_cursor():
        if visible_lines:
            visible_lines[cursor_position]['screen'].chgat(visible_lines[cursor_position]['y'],
                                                           1,
                                                           int(width / 2) - 3,
                                                           curses.color_pair(5))
            if visible_lines[cursor_position]['findit']:
                visible_lines[cursor_position]['screen'].addstr(visible_lines[cursor_position]['y'],
                                                                visible_lines[cursor_position]['findit_position'],
                                                                visible_lines[cursor_position]['findit'][1],
                                                                curses.color_pair(6) | curses.A_BOLD)
            visible_lines[cursor_position]['screen'].refresh()

    def move_cursor_down():
        nonlocal current_page
        nonlocal cursor_position
        nonlocal visible_lines
        if cursor_position + 1 == len(visible_lines) and len(visible_lines) == max_lines * 2:
            current_page += 1
            cursor_position = 0
            visible_lines = show_lines(left[0], right[0], page=current_page, max_lines=max_lines)
        else:
            cursor_position = cursor_position + 1 if cursor_position + 1 < len(visible_lines) else cursor_position

    def move_cursor_up():
        nonlocal current_page
        nonlocal cursor_position
        nonlocal visible_lines
        if current_page > 0 and cursor_position == 0:
            current_page -= 1
            visible_lines = show_lines(left[0], right[0], page=current_page, max_lines=max_lines)
            cursor_position = len(visible_lines) - 1
        else:
            cursor_position = cursor_position - 1 if cursor_position > 0 else cursor_position

    def call_search_dialog():
        nonlocal search_string
        sid = edit_box(70, 5, 5, ' Searching for... ')
        # key = 0
        while True:
            key = sid.getch()
            if key == 10:
                break
            if key == 27:
                curses.curs_set(0)
                return False
            edit_box_keyborad_processor(sid, key, search_string)
        return True

    def new_cert_dialog():
        nonlocal obj_set
        obj_set = [{'win_id': edit_box(70, 5, 5, ' Name '), 'buffer': [], 'onlydigit': False},
                   {'win_id': edit_box(70, 8, 5, ' E-mail '), 'buffer': [], 'onlydigit': False},
                   {'win_id': edit_box(70, 11, 5, ' Expired in ... '), 'buffer': [], 'onlydigit': True}]
        for obj in reversed(obj_set):
            obj['win_id'].refresh()
        cur_object = 0
        while True:
            key = obj_set[cur_object]['win_id'].getch()
            if key == 9:
                cur_object = cur_object + 1 if cur_object + 1 < len(obj_set) else 0
            if key == 10:
                break
            if key == 27:
                curses.curs_set(0)
                return False
            edit_box_keyborad_processor(obj_set[cur_object]['win_id'],
                                        key,
                                        obj_set[cur_object]['buffer'],
                                        obj_set[cur_object]['onlydigit'])
        return True

    def menu():
        offset = 0
        for item in ['Q: Exit ',
                     'S: Search ',
                     'Ctrl+V: show valid ',
                     'Ctrl+R: show revoked ',
                     'Ctrl+A: show all ',
                     'C: Gen CRL ',
                     'N: New ',
                     'P: p12 gen ',
                     'R: Revoke ']:
            menu_item = item.split(':')
            main_screen.addstr(height - 1, offset, menu_item[0], curses.color_pair(2) | curses.A_BOLD)
            main_screen.addstr(height - 1, offset + len(menu_item[0]) + 1, '%s' % menu_item[1], curses.color_pair(1))
            offset = offset + len(item) + 2

    def show_me_screen():
        nonlocal left, right, height, width, max_lines, visible_lines
        height, width = main_screen.getmaxyx()
        left, right = create_main_window(main_screen, height, width)
        max_lines = min([left[0].getmaxyx()[0], right[0].getmaxyx()[0]])
        max_lines -= 2
        visible_lines = show_lines(left[0], right[0], page=current_page, max_lines=max_lines)
        draw_cursor()
        main_screen.refresh()
        curses.panel.update_panels()
        menu()

    cursor_position = 0
    current_page = 0
    left, right, height, width = None, None, 0, 0
    max_lines = 0
    visible_lines = []
    show_me_screen()
    while True:
        pressed_key = main_screen.getch()
        main_screen.move(height - 3, 1)
        main_screen.clrtoeol()
        if pressed_key == curses.KEY_RESIZE:
            if curses.is_term_resized(height, width):
                main_screen.clear()
                main_screen.refresh()
                del left
                del right
                show_me_screen()
        if pressed_key == 258:
            clear_cursor()
            move_cursor_down()
            draw_cursor()
        if pressed_key == 99:
            generate_crl()
            visible_lines = show_lines(left[0],
                                       right[0],
                                       page=current_page,
                                       max_lines=max_lines)
        if pressed_key == 259:
            clear_cursor()
            move_cursor_up()
            draw_cursor()
        if pressed_key == 338:
            clear_cursor()
            cursor_position = len(visible_lines) - 1
            move_cursor_down()
            draw_cursor()
        if pressed_key == 339:
            clear_cursor()
            cursor_position = 0
            move_cursor_up()
            draw_cursor()
        if pressed_key == 114:
            if visible_lines[cursor_position]['Status'] == 'V':
                revoke_cert(visible_lines[cursor_position]) or generate_crl()
                visible_lines = show_lines(left[0],
                                           right[0],
                                           page=current_page,
                                           max_lines=max_lines)
            else:
                main_screen.addstr(height - 3,
                                   1,
                                   'Already revoked',
                                   curses.color_pair(7) | curses.A_BOLD | curses.A_BLINK)
        if pressed_key == 113 or pressed_key == 81:
            break
        if pressed_key == 112 or pressed_key == 80:
            try:
                p12_file_size = os.path.getsize('%s/Certs/%s.p12' % (os.environ['PKI_ROOT'],
                                                                     visible_lines[cursor_position]['CN']))
            except FileNotFoundError:
                p12_file_size = -1
            if p12_file_size <= 0 and visible_lines[cursor_position]['Status'] == 'V':
                generate_p12(visible_lines[cursor_position]['CN'])
                visible_lines = show_lines(left[0],
                                           right[0],
                                           page=current_page,
                                           max_lines=max_lines)
            else:
                main_screen.addstr(height - 3,
                                   1,
                                   'Already exist',
                                   curses.color_pair(7) | curses.A_BOLD | curses.A_BLINK)
        if pressed_key == 22:
            cursor_position = 0
            current_page = 0
            visible_lines = show_lines(left[0],
                                       right[0],
                                       page=current_page,
                                       max_lines=max_lines, findit=('Status', 'V'))
            draw_cursor()
        if pressed_key == 18:
            cursor_position = 0
            current_page = 0
            visible_lines = show_lines(left[0],
                                       right[0],
                                       page=current_page,
                                       max_lines=max_lines, findit=('Status', 'R'))
            draw_cursor()
        if pressed_key == 1:
            cursor_position = 0
            current_page = 0
            visible_lines = show_lines(left[0],
                                       right[0],
                                       page=current_page,
                                       max_lines=max_lines)
            draw_cursor()
        if pressed_key == 115 or pressed_key == 83:
            search_string = []
            cursor_position = 0
            find_str = None
            if call_search_dialog():
                find_str = ('CN', ''.join(search_string))
            visible_lines = show_lines(left[0],
                                       right[0],
                                       page=current_page,
                                       max_lines=max_lines,
                                       findit=find_str)
            draw_cursor()
        if pressed_key == 110:
            obj_set = []
            new_cert_dialog()
            if len(obj_set[0]['buffer'] and obj_set[1]['buffer'] and obj_set[2]['buffer']):
                (create_request(''.join(obj_set[0]['buffer']),
                                ''.join(obj_set[1]['buffer'])) or
                 sign_cert(''.join(obj_set[0]['buffer']),
                           ''.join(obj_set[1]['buffer']),
                           ''.join(obj_set[2]['buffer'])) or
                 generate_p12(''.join(obj_set[0]['buffer'])))
            visible_lines = show_lines(left[0],
                                       right[0],
                                       page=current_page,
                                       max_lines=max_lines)
            draw_cursor()


def edit_box(length, y_posistion, x_position, caption):
    edit_scr = curses.newwin(3, length, y_posistion, x_position)
    shadow = curses.newwin(3, length, y_posistion + 1, x_position + 1)
    edit_scr.bkgd(' ', curses.color_pair(1))
    shadow.bkgd(' ', curses.color_pair(2))
    edit_scr.clear()
    edit_scr.box()
    shadow.clear()
    shadow.refresh()
    edit_scr.addstr(0, 3, caption)
    curses.curs_set(1)
    edit_scr.keypad(0)
    edit_scr.move(1, 1)
    return edit_scr


def edit_box_keyborad_processor(scr, char, edit_string, onlydigit=False):
    height, width = scr.getmaxyx()
    if any(((48 <= char <= 57),
            (65 <= char <= 90),
            (97 <= char <= 122),
            char == 45,
            char == 95,
            char == 44,
            char == 46,
            char == 64)):
        if onlydigit and not chr(char).isdigit():
            return
        if len(edit_string) < width - 3:
            scr.addstr(1, len(edit_string) + 1, chr(char))
            edit_string.append(chr(char))
    if char == 127 and len(edit_string):
        edit_string.pop(len(edit_string) - 1)
        scr.addstr(1, len(edit_string) + 1, ' ')
    scr.move(1, len(edit_string) + 1)


def create_files(file_name, init_txt='', rand=False):
    try:
        with open(file_name, 'wb' if rand else 'w') as file_descriptor:
            if rand:
                init_txt = open('/dev/urandom', 'rb').read(1024)
            file_descriptor.write(init_txt)
            os.chmod(file_name, 0o600)
    except IOError as err:
        print('%s %s' % (file_name, os.strerror(err.errno)))
        return 1
    return 0


def create_folders(*folders):
    for file_descriptor in folders:
        try:
            os.mkdir(file_descriptor, 0o700)
        except OSError as err:
            print(file_descriptor + ' ' + os.strerror(err.errno))
            return 1
    return 0


def shell_command(shell_cmd):
    exec_status = 1
    try:
        cmd_str = shell_cmd.split(' ')
        for (i, line) in enumerate(cmd_str):
            if '~' in line:
                cmd_str[i] = cmd_str[i].replace('~', ' ')
        exec_status = subprocess.call(cmd_str, timeout=180)
    except subprocess.TimeoutExpired as err:
        print(err)
    finally:
        return exec_status


def create_ca_req():
    print('STEP 1 (create request) STEP 2 (create self-signed CA)\n\n%s\n\n\n'
          'STEP 1.>>>>>Trying to generate CA request <<<<<<\n' % ('-' * 70))
    exec_status = 1
    try:
        with open('%s%s' % (sys.argv[0][:sys.argv[0].rfind('/')], '/subj.info')) as fd:
            openssl_subj = fd.readline()
            openssl_subj = openssl_subj.replace(' ', '~')
            openssl_subj = '/'.join([openssl_subj, 'CN=CAserver'])
            exec_status = shell_command('/usr/bin/openssl req -new '
                                        '-subj %s '
                                        '-keyout %s/private/cakey.pem '
                                        '-out %s/careq.pem '
                                        '-config %s/openssl.cnf' % (openssl_subj,
                                                                    os.environ['PKI_ROOT'],
                                                                    os.environ['PKI_ROOT'],
                                                                    os.environ['PKI_ROOT']))
    except FileNotFoundError as err:
        print(err)
        input('Press ENTER to continue')
    finally:
        return exec_status


def sel_sign_ca():
    print('STEP 1 (create request) STEP 2 (create self-signed CA)\n\n%s\n\n\n'
          'STEP 2.>>>>>Trying to create self-signed CA <<<<<<\n\n' % ('-' * 70))
    exit_status = shell_command('/usr/bin/openssl ca '
                                '-create_serial -out %s/cacert.pem '
                                '-keyfile %s/private/cakey.pem '
                                '-selfsign -extensions v3_ca -config %s/openssl.cnf '
                                '-in %s/careq.pem' % (os.environ['PKI_ROOT'],
                                                      os.environ['PKI_ROOT'],
                                                      os.environ['PKI_ROOT'],
                                                      os.environ['PKI_ROOT']))
    if exit_status:
        print('(create self-signed CA) >>>>>FAILED<<<<<<')
        input('Press ENTER to continue')
    print('\n\n\n')
    return exit_status


def prepare2run_shellcommand():
    curses.endwin()
    shell_command('clear')


def generate_crl():
    if not curses.isendwin():
        prepare2run_shellcommand()
    print('STEP 1 (revoke cert) STEP 2 (generate CRL)\n\n%s\n\n\n'
          'STEP 2.>>>>>Trying to generate CRL<<<<<<\n\n' % ('-' * 70))
    exit_status = shell_command('/usr/bin/openssl ca -gencrl '
                                '-out %s/crl.pem '
                                '-config %s/openssl.cnf' % (os.environ['PKI_ROOT'],
                                                            os.environ['PKI_ROOT']))
    crl_hook = sys.argv[0][:sys.argv[0].rfind('/')]
    if (not exit_status and
            os.path.exists(crl_hook + '/hooks/crl.hook') and
            os.path.getsize(crl_hook + '/hooks/crl.hook') > 0):
        hook_stat = shell_command(crl_hook + '/hooks/crl.hook')
        if hook_stat:
            print('CRL hook execution >>>>>FAILED<<<<<<')
            input('Press ENTER to continue')
    elif exit_status:
        print('STEP 2 (generate CRL) >>>>>FAILED<<<<<<')
        input('Press ENTER to continue')
    print('\n\n')
    return exit_status


def revoke_cert(cert_detail):
    if not curses.isendwin():
        prepare2run_shellcommand()
    print('STEP 1 (revoke cert) STEP 2 (generate CRL)\n\n%s\n\n\n'
          'STEP 1.>>>>>Trying to revoke %s<<<<<<\n\n' % ('-' * 70, cert_detail['cert_file_name']))
    exit_status = shell_command('/usr/bin/openssl ca -revoke %s/signed_certs/%s.pem -config %s/openssl.cnf' %
                                (os.environ['PKI_ROOT'], cert_detail['cert_file_name'], os.environ['PKI_ROOT']))
    revoke_hook = sys.argv[0][:sys.argv[0].rfind('/')]
    if (not exit_status and
            os.path.exists(revoke_hook + '/hooks/revoke.hook') and
            os.path.getsize(revoke_hook + '/hooks/revoke.hook') > 0):
        hook_stat = shell_command('%s/hooks/revoke.hook %s %s %s' %
                                  (revoke_hook,
                                   cert_detail['cert_file_name'],
                                   cert_detail['CN'],
                                   cert_detail['emailAddress']))
        if hook_stat:
            print('CRL hook execution >>>>>FAILED<<<<<<')
            input('Press ENTER to continue')
    elif exit_status:
        print('(revoke cert)>>>>>FAILED<<<<<<')
        input('Press ENTER to continue')
    print('\n\n')
    return exit_status


def create_request(cn, email):
    if not curses.isendwin():
        prepare2run_shellcommand()
    print('STEP 1 (create request) STEP 2 (sign request) STEP3 (generate p12)\n\n%s\n\n\n'
          'STEP 1.>>>>>Trying to generate request for %s<<<<<<\n\n' % ('-' * 70, cn))
    try:
        openssl_subj = open(sys.argv[0][:sys.argv[0].rfind('/')] + '/subj.info').readline()
    except IOError as err:
        print(' '.join('%s/subj.info' % [sys.argv[0][:sys.argv[0].rfind('/')],
                                         os.strerror(err.errno),
                                         '\n(create request) >>>>>FAILED<<<<<<']))
        input('Press ENTER to continue')
        return 1
    openssl_subj = openssl_subj.replace(' ', '~')
    openssl_subj = '/'.join([openssl_subj,
                             'CN=%s' % cn,
                             'emailAddress=%s' % email if email else ''])
    exit_status = shell_command('/usr/bin/openssl req -new '
                                '-config %s/openssl.cnf '
                                '-subj %s '
                                '-keyout %s/Certs/%s_key.pem '
                                '-out %s/Certs/%s_req.pem' %
                                (os.environ['PKI_ROOT'],
                                 openssl_subj,
                                 os.environ['PKI_ROOT'],
                                 cn,
                                 os.environ['PKI_ROOT'],
                                 cn))
    if exit_status:
        input('Press ENTER to continue')
    print('\n\n\n')
    return exit_status


def sign_cert(cn, email, days):
    if not curses.isendwin():
        prepare2run_shellcommand()
    print('STEP 1 (create request) STEP 2 (sign request) STEP3 (generate p12)\n\n%s\n\n\n'
          'STEP 2. >>>>>Trying to sign request %s<<<<<<\n\n' % ('-' * 70, cn))
    exit_status = shell_command('/usr/bin/openssl ca '
                                '-config %s/openssl.cnf '
                                '-days %s '
                                '-in %s/Certs/%s_req.pem '
                                '-out %s/Certs/%s_cert.pem' %
                                (os.environ['PKI_ROOT'],
                                 days,
                                 os.environ['PKI_ROOT'],
                                 cn,
                                 os.environ['PKI_ROOT'],
                                 cn))
    new_cert_hook = sys.argv[0][:sys.argv[0].rfind('/')]
    if (not exit_status and
            os.path.exists(new_cert_hook + '/hooks/new.hook') and
            os.path.getsize(new_cert_hook + '/hooks/new.hook') > 0):
        hook_stat = shell_command('%s/hooks/new.hook %s %s %s' % (new_cert_hook, cn, email, days))
        if hook_stat:
            print('CRL hook execution >>>>>FAILED<<<<<<')
            input('Press ENTER to continue')
    elif exit_status:
        print('(sign request) >>>>>FAILED<<<<<<')
        input('Press ENTER to continue')
    print('\n\n\n')
    return exit_status


def generate_p12(cn):
    if not curses.isendwin():
        prepare2run_shellcommand()
    print('STEP 1 (create request) STEP 2 (sign request) STEP3 (generate p12)\n\n%s\n\n\n'
          'STEP 3. >>>>>Trying to generate p12 key<<<<<<\n\n' % ('-' * 70))
    exit_status = shell_command('/usr/bin/openssl pkcs12 -export -clcerts '
                                '-in %s/Certs/%s_cert.pem '
                                '-inkey %s/Certs/%s_key.pem -out %s/Certs/%s.p12' %
                                (os.environ['PKI_ROOT'],
                                 cn,
                                 os.environ['PKI_ROOT'],
                                 cn,
                                 os.environ['PKI_ROOT'],
                                 cn))
    if exit_status:
        print('(generate p12) >>>>>FAILED<<<<<<')
    try:
        if os.path.getsize('%s/Certs/%s.p12' % (os.environ['PKI_ROOT'], cn)) == 0:
            print('%s/Certs/%s.p12 is empty. Removing it ' % (os.environ['PKI_ROOT'], cn))
            os.remove('%s/Certs/%s.p12' % (os.environ['PKI_ROOT'], cn))
    except OSError as err:
        print(os.strerror(err.errno))
    finally:
        return exit_status


if __name__ == '__main__':
    if not os.environ.get('PKI_ROOT'):
        print('Please set $PKI_ROOT variable \n\npress any key to continue \n')
    else:
        shell_command("clear")
        if 'create' in sys.argv[1:]:
            create_folders('%s%s' % (os.environ['PKI_ROOT'], '/private'),
                           '%s%s' % (os.environ['PKI_ROOT'], '/Certs'),
                           '%s%s' % (os.environ['PKI_ROOT'], '/signed_certs'),
                           '%s%s' % (sys.argv[0][:sys.argv[0].rfind('/')], '/hooks'))
            stat = (create_files('%s%s' % (os.environ['PKI_ROOT'], '/index.txt')) or
                    create_files('%s%s' % (os.environ['PKI_ROOT'], '/crlnumber'), init_txt='03') or
                    create_files('%s%s' % (sys.argv[0][:sys.argv[0].rfind('/')], '/subj.info'),
                                 init_txt='/OU=smth/O=Example Corp/C=SM/ST=Anything/L=My_place') or
                    create_files('%s%s' % (os.environ['PKI_ROOT'], '/random'), rand=True) or
                    create_files('%s%s' % (sys.argv[0][:sys.argv[0].rfind('/')], '/hooks/crl.hook')) or
                    create_files('%s%s' % (sys.argv[0][:sys.argv[0].rfind('/')], '/hooks/new.hook')) or
                    create_files('%s%s' % (sys.argv[0][:sys.argv[0].rfind('/')], '/hooks/revoke.hook')))
            if not stat:
                os.chmod(sys.argv[0][:sys.argv[0].rfind('/')] + '/hooks/revoke.hook', 0o700)
                os.chmod(sys.argv[0][:sys.argv[0].rfind('/')] + '/hooks/crl.hook', 0o700)
                os.chmod(sys.argv[0][:sys.argv[0].rfind('/')] + '/hooks/new.hook', 0o700)
                print('Please edit subj.info file.\n'
                      'It contains all necessary information for generating certs\n'
                      'Then run "pky.py init" command\n')
        elif 'init' in sys.argv[1:]:
            if not shell_command('openssl version'):
                create_ca_req() or sel_sign_ca()
            else:
                print('Can not find openssl.\nsudo apt-get install openssl.\n')
        else:
            if os.path.exists(os.environ.get('PKI_ROOT') + '/index.txt'):
                screen = init_curses()
                keyborad_processor(screen)
                shutdown_curses(screen)
            else:
                print('ERROR\n '
                      '%s is not initialized\n'
                      'Run %s  create first.' % (os.environ.get('PKI_ROOT'), sys.argv[0]))
