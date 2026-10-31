# Direct-Pairwise Registration Path Repair V1

The first dispatcher reached four workers, but each stopped before its first
training update because corpus audit paths were registered relative to the
login-node working directory and resolved differently on worker nodes.

This repair resolves the existing root directory before writing registrations.
It changes no corpus bytes, split, seed, model, update budget, pair label,
control, or qualification threshold. The failed controls and logs are retained;
all nine workers run in newly named execution and control directories.
