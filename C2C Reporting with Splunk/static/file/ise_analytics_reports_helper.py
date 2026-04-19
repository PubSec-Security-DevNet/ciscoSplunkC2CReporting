import csv
import time
import re
import cisco_catalyst_exceptions as cce
from hashlib import sha3_512
from io import StringIO
import paramiko
import utils



class CiscoISEAnalyticsReports:
    """ISE Analytics Reports base class."""

    def __init__(
        self,
        logger,
        input_name
    ):
        """Initialize class."""
        self.logger = logger
        self.input_name = input_name

    def _clear_buffer(self, channel):
        """Clears the SSH receive buffer."""
        time.sleep(1)
        while channel.recv_ready():
            channel.recv(65535)

    def _check_stale_and_set_term(self, channel, username):
        """
        Checks for stale SSH sessions and sets ISE terminal length 0 for the session.

        :param channel: SSH channel for command execution
        :param username: SSH username
        :raises: Logging Error on detection of stale SSH sessions identified on the ISE Node.
        """
        time.sleep(2)
        if channel.recv_ready():
            output = channel.recv(65535).decode('utf-8')
            if "Enter session number to resume or press <Enter> to start a new one" in output:
                self.logger.error(
                    f"STALE SESSION DETECTED for user: {username}. Please execute 'forceout {username}' on ISE CLI."
                )
                return False
        
        self.logger.debug("Setting terminal length to 0")
        channel.send('terminal length 0\r\n')
        self._clear_buffer(channel)
        return True

    def establish_ssh_connection(self, host, port, username, password, connection_name, timeout=30):
        """
        Establish SSH connection and return SSH client and channel.

        :param host: Host IP or hostname
        :param port: SSH port number
        :param username: SSH username
        :param password: SSH password
        :param connection_name: Name for logging (e.g., "ISE" or "Repository")
        :param timeout: Connection timeout in seconds
        :return: Tuple of (ssh_client, channel) if successful
        :raises: cce.AuthenticationError on connection failures
        """
        ssh = None
        channel = None
        try:
            paramiko.PKey.get_fingerprint = lambda x: sha3_512(x.asbytes()).digest()
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.logger.info("Connecting to {} server: '{}'.".format(connection_name, host))
            ssh.connect(host, int(port), username, password, timeout=timeout)
            transport = ssh.get_transport()
            transport.set_keepalive(30)
            channel = ssh.invoke_shell()
            
            # --- Added Stale Check and Terminal Logic ---
            if not self._check_stale_and_set_term(channel, username):
                channel.close()
                ssh.close()
                self.logger.error(f"Stale session detected for {username}")
                raise cce.AuthenticationError(f"Stale session detected for {username}")

            self.logger.debug("Successfully connected to {} server: '{}'.".format(connection_name, host))
            return ssh, channel
        except paramiko.AuthenticationException as e:
            self.logger.error(
                "Authentication failed while connecting to {} server '{}': {}. Please verify"
                " provided {} Username or Password".format(
                    connection_name, host, str(e), connection_name
                ))
            raise cce.AuthenticationError(
                "Failed to authenticate with {} server '{}'.".format(connection_name, host)
            )
        except paramiko.SSHException as e:
            self.logger.error("SSH error while connecting to {} server '{}': {}.".format(connection_name, host, str(e)))
            raise cce.AuthenticationError("SSH connection error to {} server '{}'.".format(connection_name, host))
        except Exception as e:
            self.logger.error("Error connecting to {} server '{}': {}.".format(connection_name, host, str(e)))
            raise cce.AuthenticationError("Failed to connect to {} server '{}'.".format(connection_name, host))

    def establish_sftp_connection(self, host, port, username, password, connection_name, timeout=30):
        """
        Establish SFTP connection and return SSH client and SFTP client.

        :param host: Host IP or hostname
        :param port: SSH port number
        :param username: SSH username
        :param password: SSH password
        :param connection_name: Name for logging (e.g., "ISE" or "Repository")
        :param timeout: Connection timeout in seconds
        :return: Tuple of (ssh_client, sftp_client) if successful
        :raises: cce.AuthenticationError on connection failures
        """
        ssh = None
        sftp = None
        try:
            paramiko.PKey.get_fingerprint = lambda x: sha3_512(x.asbytes()).digest()
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.logger.debug("Connecting to {} server: '{}'.".format(connection_name, host))
            ssh.connect(host, int(port), username, password, timeout=timeout)
            transport = ssh.get_transport()
            transport.set_keepalive(30)
            sftp = ssh.open_sftp()
            time.sleep(5)
            self.logger.debug("Successfully connected to {} server: '{}'.".format(connection_name, host))
            return ssh, sftp
        except paramiko.AuthenticationException as e:
            self.logger.error(
                "Authentication failed while connecting to {} server '{}': {}. Please verify"
                " provided {} Username or Password".format(
                    connection_name, host, str(e), connection_name
                ))
            raise cce.AuthenticationError(
                "Failed to authenticate with {} server '{}'.".format(connection_name, host)
            )
        except paramiko.SSHException as e:
            self.logger.error("SSH error while connecting to {} server '{}': {}.".format(connection_name, host, str(e)))
            raise cce.AuthenticationError("SSH connection error to {} server '{}'.".format(connection_name, host))
        except Exception as e:
            self.logger.error("Error connecting to {} server '{}': {}.".format(connection_name, host, str(e)))
            raise cce.AuthenticationError("Failed to connect to {} server '{}'.".format(connection_name, host))

    def generate_all_endpoints_report(self, channel):
        """Generate All Endpoints report using option 16.
        
        Args:
            channel: SSH channel for command execution

        Returns:
            List of CSV files found in the output, empty list if failed
        """
        self.logger.info("Running Option 16 Reports to generate All Endpoints report")
        channel.send('16\n')
        time.sleep(15)

        report_generated = ""
        report_timer = 0
        while report_timer < 30:
            while channel.recv_ready():
                report_generated += channel.recv(65535).decode('utf-8')
            if "Completed generating All Endpoints report" in report_generated:
                csv_files = re.findall(r'\bFullReport.*?\.csv\b', report_generated)
                self.logger.info("ISE PAN Option 16 completed successfully. All Endpoints report generated.")
                return csv_files
            elif report_timer >= 30:
                self.logger.error(
                    "All Endpoints report not generated within the expected time (30 minutes). Exiting."
                )
                return []
            else:
                report_timer += 1
                self.logger.debug("Waiting for All Endpoints report generation to complete...")
                time.sleep(30)
        return []

    def generate_posture_reports(self, channel):
        """Generate Posture reports using option 17 or individual export options 2, 4, 5."""
        report_generated = ""
        self.logger.info("Trying Option 17 Reports to generate Posture reports")
        
        option17 = True
        channel.send('17\n')
        time.sleep(5)
        
        report_check = ""
        while channel.recv_ready():
            report_check += channel.recv(65535).decode('utf-8')

        if "Illegal option" in report_check:
            option17 = False
            self.logger.info("Option 17 is not available. Using export custom-reports individual export options: 2, 4, 5")
            channel.send('0\r\n')
            time.sleep(5)
            channel.send('export custom-reports\n')
            time.sleep(5)

            csvs2, csvs3, csvs4 = [], [], []
            options_map = {
                '2': {'pattern': r'\bPosture_Registry_Report.*?\.csv\b', 'success_msg': "Completed generating registry report", 'name': "Registry Report"},
                '4': {'pattern': r'\bPosture_Hardware_Report.*?\.csv\b', 'success_msg': "Completed generating All Endpoints hardware report", 'name': "Hardware Report"},
                '5': {'pattern': r'\bPosture_Application_Report.*?\.csv\b', 'success_msg': "Completed generating All Endpoints application report", 'name': "Application Report"}
            }

            for opt, config in options_map.items():
                success = False
                retry_count = 0
                while not success and retry_count < 3:
                    if retry_count == 0:
                        self.logger.info(f"Sending Option {opt} - Exporting report: {config['name']}")
                    elif retry_count >= 1:
                        attempts_left = 5 - retry_count
                        self.logger.info(f"Retrying Option {opt} - Exporting report: {config['name']} : {attempts_left} tries remaining")
                    channel.send(f'{opt}\n')
                    
                    wait_timer = 0
                    while wait_timer < 40:
                        time.sleep(3)
                        report_generated = ""
                        while channel.recv_ready():
                            report_generated += channel.recv(65535).decode('utf-8')
                        
                        if "please try again later" in report_generated:
                            self.logger.info("Another Export in progress. Backing off for 2 minutes...")
                            time.sleep(120)
                            self._clear_buffer(channel)
                            retry_count += 1
                            break # Break wait_timer to re-send the option
                        
                        if config['success_msg'] in report_generated:
                            self.logger.info(f"Successfully generated report for Option {opt}.")
                            found = re.findall(config['pattern'], report_generated)
                            if opt == '2': csvs2 = found
                            elif opt == '4': csvs3 = found
                            elif opt == '5': csvs4 = found
                            success = True
                            break
                        wait_timer += 1
                        self.logger.info(f"Option {opt} - {config['name']} in progress. Please Wait...")
                        time.sleep(30)

                    if not success and retry_count >= 4:
                        self.logger.error(f"Failed to generate report for Option {opt} after retries. Stopping.")
                        return [], [], []
            
            return csvs2, csvs3, csvs4

        else:
            time.sleep(15)
            report_timer = 0
            while report_timer < 30:
                while channel.recv_ready():
                    report_generated += channel.recv(65535).decode('utf-8')
                if "Posture_Application_Report" in report_generated:
                    csvs2 = re.findall(r'\bPosture_Registry_Report.*?\.csv\b', report_generated)
                    csvs3 = re.findall(r'\bPosture_Hardware_Report.*?\.csv\b', report_generated)
                    csvs4 = re.findall(r'\bPosture_Application_Report.*?\.csv\b', report_generated)
                    return csvs2, csvs3, csvs4
                report_timer += 1
                time.sleep(30)
        
        return [], [], []

    def collect_csv_files(self, csvs1, csvs2, csvs3, csvs4, channel):
        """Collect and deduplicate CSV files from all report types.

        Args:
            csvs1: FullReport CSV files
            csvs2: Posture Registry CSV files
            csvs3: Posture Hardware CSV files
            csvs4: Posture Application CSV files
            channel: SSH channel for final command

        Returns:
            List of unique CSV filenames
        """
        channel.send('0\r\n')
        # Clear buffer after exiting application menu
        self._clear_buffer(channel)
        all_csvs = list(set(csvs1 + csvs2 + csvs3 + csvs4))
        csv_files = []
        for file in all_csvs:
            csv_files.append(file)
        return csv_files

    def run_reports(
        self,
        ise_cli_address,
        ise_cli_username,
        ise_cli_password,
        ise_ssh_port
    ):
        """Run command in ISE CLI and fetch reports."""
        csv_files = []
        ssh = None
        channel = None

        try:
            ssh, channel = self.establish_ssh_connection(
                ise_cli_address, ise_ssh_port, ise_cli_username, ise_cli_password, "ISE"
            )
            self.logger.info(
                f"instance={self.input_name}, "
                "product=Cisco ISE, "
                f"filter_value=cisco_catalyst_ise_analytics_reports://{self.input_name}, "
                "status=Connected,"
            )

            time.sleep(2)
            self.logger.debug("Entering 'application configure ise'")
            channel.send('application configure ise\r\n')
            time.sleep(2)

            # Generate All Endpoints report
            csvs1 = self.generate_all_endpoints_report(channel)

            # Generate Posture reports
            csvs2, csvs3, csvs4 = self.generate_posture_reports(channel)

            # Collect and return CSV files
            csv_files = self.collect_csv_files(csvs1, csvs2, csvs3, csvs4, channel)

        except Exception as e:
            self.logger.error(
                "Error during command execution while generating reports on ISE server '{}': {}.".format(
                    ise_cli_address, str(e)
                ))
        finally:
            try:
                if channel:
                    # --- Added Clean Logout ---
                    channel.send('exit\r\n')
                    time.sleep(10)
                    channel.close()
                if ssh:
                    ssh.close()
                self.logger.debug("SSH connection to ISE server '{}' closed.".format(ise_cli_address))
            except Exception as e:
                self.logger.debug(
                    "Error closing SSH connection to ISE server '{}': {}.".format(
                        ise_cli_address, str(e)
                    ))
        return csv_files

    def check_report_on_disk(self, channel, report, ise_disk_name):
        """Check if report exists on ISE local disk.

        Args:
            channel: SSH channel for command execution
            report: Report filename to check
            ise_disk_name: Name of the ISE disk repository

        Returns:
            True if report found on disk, False otherwise
        """
        disk_timer = 0
        while disk_timer < 10:
            output = ""
            time.sleep(2)
            channel.send(f"show repository {ise_disk_name}\r\n")
            time.sleep(13)  # Allow time for command to process
            while channel.recv_ready():
                output += channel.recv(65535).decode('utf-8')
            if report in output:
                self.logger.info(
                    "Report '{}' located on ISE local disk. Preparing for transfer to repository.".format(
                        report
                    )
                )
                return True
            else:
                self.logger.debug("Searching for report '{}' in ISE Local Disk. Waiting...".format(report))
                disk_timer += 1
        return False

    def transfer_report_to_repository(self, channel, report, ise_repository_name):
        """Initiate transfer of report from disk to repository and check for host key errors.

        Args:
            channel: SSH channel for command execution
            report: Report filename to transfer
            ise_repository_name: Name of the target repository
        
        Returns:
            True if the command was accepted, False if host key error is detected.
        """
        self.logger.info(
            "Transferring report '{}' to repository: '{}'.".format(
                report, ise_repository_name
            )
        )
        channel.send(f"copy disk:/{report} repository {ise_repository_name}\r\n")
        
        time.sleep(5)
        output = ""
        while channel.recv_ready():
            output += channel.recv(65535).decode('utf-8')
            
        if "Please add the host key using the crypto host_key exec command" in output:
            self.logger.error(
                "Host key verification failed on ISE for repository '{}'. "
                "Error: 'Please add the host key using the crypto host_key exec command'. "
                "Aborting transfer.".format(ise_repository_name)
            )
            return False
        elif "fail" in output:
                self.logger.error(f"Report {report} copy to {ise_repository_name} failed. Disconnecting from ISE PAN.")
                return False
            
        return True

    def verify_transfer_completion(self, channel, report, ise_repository_name):
        """Verify that the report transfer completed successfully.

        Args:
            channel: SSH channel for command execution
            report: Report filename to verify
            ise_repository_name: Name of the target repository

        Returns:
            True if transfer completed successfully, False otherwise
        """
        csv_timer = 0
        self._clear_buffer(channel)
        while csv_timer < 10:
            ade_output = ""
            channel.send(f"show repository {ise_repository_name}\r\n")
            time.sleep(2)
            while channel.recv_ready():
                ade_output += channel.recv(65535).decode('utf-8')
            if report in ade_output:
                self.logger.info(
                    "Report '{}' successfully transferred to repository: '{}'.".format(
                        report, ise_repository_name
                    )
                )
                # Clear buffer after verification
                self._clear_buffer(channel)
                return True
            elif "fail" in ade_output:
                self.logger.error("Report '{}' transfer failed. Disconnecting from ISE PAN.".format(report))
                return False
            else:
                self.logger.debug(
                    "Waiting for report '{}' transfer to repository '{}' to complete...".format(
                        report, ise_repository_name
                    )
                )
                csv_timer += 1
                time.sleep(30)

        self.logger.error(
            "Report '{}' transfer did not complete within the expected time."
            " Disconnecting from ISE PAN.".format(report)
        )
        return False

    def move_report(
        self,
        ise_cli_address,
        ise_cli_username,
        ise_cli_password,
        ise_ssh_port,
        report,
        ise_disk_name,
        ise_repository_name
    ):
        """Move reports into SFTP repository."""
        csv_transferred = False
        ssh = None
        channel = None

        try:
            ssh, channel = self.establish_ssh_connection(
                ise_cli_address, ise_ssh_port, ise_cli_username, ise_cli_password, "ISE"
            )
            self.logger.debug(
                "Successfully connected to ISE server '{}' for report transfer.".format(
                    ise_cli_address
                ))

            # Check if report exists on disk
            csv_on_disk = self.check_report_on_disk(channel, report, ise_disk_name)

            if not csv_on_disk:
                self.logger.error(
                    "Report '{}' was not located on ISE local disk for transfer. SSH connection closed.".format(
                        report
                    )
                )
                return False

            # Transfer report to repository and check for host key errors
            if not self.transfer_report_to_repository(channel, report, ise_repository_name):
                return False

            self._clear_buffer(channel)

            # Verify transfer completion
            csv_transferred = self.verify_transfer_completion(channel, report, ise_repository_name)

        except Exception as e:
            self.logger.error(
                "Error during command execution while transferring report '{}' on ISE server '{}': {}.".format(
                    report, ise_cli_address, str(e)
                )
            )
        finally:
            try:
                if channel:
                    channel.send('exit\r\n')
                    time.sleep(10)
                    channel.close()
                if ssh:
                    ssh.close()
                self.logger.debug(
                    "SSH connection to ISE server '{}' closed.".format(
                        ise_cli_address
                    )
                )
            except Exception as e:
                self.logger.debug(
                    "Error closing SSH connection to ISE server '{}': {}.".format(
                        ise_cli_address, str(e)
                    )
                )
        return csv_transferred

    def read_csv_from_sftp_and_convert(
        self,
        repository_host_address,
        repository_port,
        repository_host_username,
        repository_host_password,
        repository_path,
        report
    ):
        """Read CSV from SFTP repository and convert to JSON in memory."""
        ssh = None
        sftp = None
        try:
            ssh, sftp = self.establish_sftp_connection(
                repository_host_address, repository_port, repository_host_username,
                repository_host_password, "SFTP repository"
            )

            try:
                remote_file_path = repository_path + report
                self.logger.info("Reading CSV file '{}' from SFTP repository.".format(report))

                with sftp.open(remote_file_path, 'r') as remote_file:
                    # Read file content
                    file_content = remote_file.read().decode("utf-8")
                    time.sleep(5)

                # Process CSV content in memory
                csv_io = StringIO(file_content)

                # Handle delimiter detection (check for sep= in first line)
                first_line = csv_io.readline()

                delimiter = ','
                if first_line.strip().lower().startswith("sep="):
                    header_line = csv_io.readline().strip()
                    delimiter = ';'
                else:
                    header_line = first_line.strip()

                # Parse headers
                headers = [h.strip().strip('"') for h in header_line.split(delimiter)]
                reader = csv.DictReader(csv_io, fieldnames=headers, delimiter=delimiter)

                # Convert to JSON data
                data = []
                for row in reader:
                    if any(row.values()):
                        data.append(utils.clean_row(row))

                self.logger.info(
                    "Converted report '{}' to JSON in memory. Total records: {}.".format(
                        report, len(data)
                    )
                )
                return data

            except Exception as e:
                self.logger.error(
                    "Error reading or converting report '{}' from SFTP repository '{}': {}.".format(
                        report, repository_host_address, str(e)
                    )
                )
                raise cce.ISEReportsConverting(e)
            finally:
                try:
                    if sftp:
                        sftp.close()
                    if ssh:
                        ssh.close()
                    self.logger.debug(
                        "SSH connection to SFTP repository '{}' closed.".format(
                            repository_host_address
                        )
                    )
                except Exception as e:
                    self.logger.debug(
                        "Error closing SSH connection to SFTP repository '{}': {}.".format(
                            repository_host_address, str(e)
                        )
                    )

        except cce.AuthenticationError as e:
            raise cce.AuthenticationError(str(e))
        