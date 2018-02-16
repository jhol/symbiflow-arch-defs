#!/usr/bin/env python3
"""
Generate MUX.

MUXes come in two types,
 1) Configurable via logic signals,
 2) Statically configured by PnR (called "routing") muxes.
"""

import argparse
import io
import itertools
import lxml.etree as ET
import math
import os
import sys

from lib import mux as mux_lib
from lib.argparse_extra import ActionStoreBool
from lib.asserts import assert_eq

parser = argparse.ArgumentParser(
    description='Generate a MUX wrapper.',
    fromfile_prefix_chars='@',
    prefix_chars='-~'
)

parser.add_argument(
    '--width', type=int, default=8,
    help="Width of the MUX.")

parser.add_argument(
    '--type', choices=['logic', 'routing'],
    default='logic',
    help="Type of MUX.")

parser.add_argument(
    '--split-inputs', '--no-split-inputs',
    action=ActionStoreBool, default=False,
    help="Split the inputs into separate signals")

parser.add_argument(
    '--split-selects', '--no-split-selects',
    type=ActionStoreBool, default=False,
    help="Split the selects into separate signals")

parser.add_argument(
    '--name-mux', type=str, default='MUX',
    help="Name of the mux.")

parser.add_argument(
    '--name-input', type=str, default='I',
    help="Name of the input values for the mux.")

parser.name_inputs = parser.add_argument(
    '--name-inputs', type=str, default=None,
    help="Comma deliminator list for the name of each input to the mux (implies --split-inputs).")

parser.add_argument(
    '--name-output', type=str, default='O',
    help="Name of the output value for the mux.")

parser.add_argument(
    '--name-select', type=str, default='S',
    help="Name of the select parameter for the mux.")

parser.name_select = parser.add_argument(
    '--name-selects', type=str, default=None,
    help="Comma deliminator list for the name of each select to the mux (implies --split-selects).")

parser.add_argument(
    '--order', choices=[''.join(x) for x in itertools.permutations('ios')]+[''.join(x) for x in itertools.permutations('io')],
    default='iso',
    help="""Order of the arguments for the MUX. (i - Inputs, o - Output, s - Select)""")

parser.add_argument(
    '--outdir', default=None,
    help="""Directory to output generated content too.""")

parser.add_argument(
    '--comment', default=None,
    help="""Add some type of comment to the mux.""")

parser.add_argument(
    '--num_pb', default=1,
    help="""Set the num_pb for the mux.""")

parser.add_argument(
    '--subckt', default=None,
    help="""Override the subcircuit name.""")


def output_block(name, s):
    print()
    print(name, '-'*(75-(len(name)+1)))
    print(s, end="")
    if s[-1] != '\n':
        print()
    print('-'*75)

call_args = list(sys.argv)

args = parser.parse_args()
args.width_bits = mux_lib.clog2(args.width)

mypath = __file__
mydir = os.path.dirname(mypath)

if not args.outdir:
    outdir = os.path.join(".", args.name_mux.lower())
else:
    outdir = args.outdir

mux_dir = os.path.relpath(os.path.abspath(os.path.join(mydir, '..', 'vpr', 'muxes')), outdir)
buf_dir = os.path.relpath(os.path.abspath(os.path.join(mydir, '..', 'vpr', 'buf')), outdir)
mux_mk = os.path.relpath(os.path.abspath(os.path.join(mydir, '..', 'common', 'make', 'mux.mk')), outdir)

if args.name_inputs:
    assert_eq(args.name_input, parser.get_default("name_input"))
    args.name_input = None
    args.split_inputs = True

    names = args.name_inputs.split(',')
    assert len(names) == args.width, "%s input names, but %s needed." % (names, args.width)
    args.name_inputs = names
elif args.split_inputs:
    args.name_inputs = [args.name_input+str(i) for i in range(args.width)]
    parser.name_inputs.default = args.name_inputs
    assert_eq(parser.get_default("name_inputs"), args.name_inputs)

if args.name_selects:
    assert_eq(args.name_select, parser.get_default("name_select"))
    args.name_select = None
    args.split_selects = True

    names = args.name_selects.split(',')
    assert len(names) == args.width, "%s select names, but %s needed." % (names, args.width_bits)
    args.name_selects = names
elif args.split_selects:
    args.name_selects = [args.name_select+str(i) for i in range(args.width_bits)]
    parser.name_selects.default = args.name_selects
    assert_eq(parser.get_default("name_selects"), args.name_selects)

os.makedirs(outdir, exist_ok=True)

# Generated headers
generated_with = """
Generated with mux_gen.py, run 'make' in the following to regenerate in this directory;
%s
""".format(outdir)
if args.comment:
    generated_with += args.comment

# XML Files can't have "--" in them, so instead we use ~~
xml_comment = """
Generated with %s
""" % mypath
if args.comment:
    xml_comment += "\n"
    xml_comment += args.comment.replace("--", "~~")
    xml_comment += "\n"

# ------------------------------------------------------------------------
# Create a makefile to regenerate files.
# ------------------------------------------------------------------------
makefile_file = os.path.join(outdir, "Makefile.mux")
output_files = ['model.xml', 'pb_type.xml', '.gitignore', 'sim.v', 'Makefile.mux']
commit_files = ['.gitignore', "Makefile.mux"]
remove_files = [f for f in output_files if f not in commit_files]

new_makefile_contents = io.StringIO()
if True:
    f = new_makefile_contents
    # Comment goes first so it is the first thing people see.
    if args.comment:
        print("MUX_COMMENT = {}".format(args.comment), file=f)

    # Required values
    print("MUX_TYPE = {}".format(args.type.lower()), file=f)
    print("MUX_NAME = {}".format(args.name_mux), file=f)
    print("MUX_WIDTH = {}".format(args.width), file=f)

    # Optional values
    if args.split_inputs:
        print("MUX_SPLIT_INPUTS = 1", file=f)
        if args.name_inputs != parser.get_default('name_inputs'):
            print("MUX_INPUTS = {}".format(",".join(args.name_inputs)), file=f)
    else:
        if args.name_input != parser.get_default('name_input'):
            print("MUX_INPUT = {}".format(args.name_input), file=f)

    if args.split_selects:
        print("MUX_SPLIT_SELECTS = 1", file=f)
        if args.name_selects != parser.get_default('name_selects'):
            print("MUX_SELECTS = {}".format(args.name_selects), file=f)
    else:
        if args.name_select != parser.get_default('name_select'):
            print("MUX_SELECT = {}".format(args.name_select), file=f)

    if args.name_output != parser.get_default('name_output'):
        print("MUX_OUTPUT = {}".format(args.name_output), file=f)

    if args.order != parser.get_default('order'):
        print("MUX_ORDER = {}".format(args.order), file=f)

    if args.subckt != parser.get_default('subckt'):
        print("MUX_SUBCKT = {}".format(args.subckt), file=f)

    print("include {}".format(mux_mk), file=f)

new_makefile_contents = new_makefile_contents.getvalue()
if not os.path.exists(makefile_file):
    current_makefile_contents = ""
else:
    current_makefile_contents = open(makefile_file, "r").read()

if current_makefile_contents != new_makefile_contents:
    open(makefile_file, "w").write(new_makefile_contents)

output_block("Makefile.mux", open(makefile_file).read())

# ------------------------------------------------------------------------
# Create .gitignore file for the generated files.
# ------------------------------------------------------------------------
gitignore_file = os.path.join(outdir, ".gitignore")
with open(gitignore_file, "w") as f:
    f.write(".mux_gen.stamp\n")
    for name in remove_files:
        f.write(name+'\n')

output_block(".gitignore", open(gitignore_file).read())

# ------------------------------------------------------------------------
# Work out the port and their names
# ------------------------------------------------------------------------

port_names = []
for i in args.order:
    if i == 'i':
        if args.split_inputs:
            port_names.extend((mux_lib.MuxPinType.INPUT, args.name_inputs[j], 1, '[%i]' % j) for j in range(args.width))
        else:
            port_names.append((mux_lib.MuxPinType.INPUT, args.name_input, args.width, '[%i:0]' % args.width))
    elif i == 's':
        if args.split_selects and args.width_bits > 1:
            port_names.extend((mux_lib.MuxPinType.SELECT, args.name_selects[j], 1, '[%i]' % j) for j in range(args.width_bits))
        else:
            port_names.append((mux_lib.MuxPinType.SELECT, args.name_select, args.width_bits, '[%i:0]' % args.width_bits))
    elif i == 'o':
        port_names.append((mux_lib.MuxPinType.OUTPUT, args.name_output, 1, ''))

# ------------------------------------------------------------------------
# Generate the sim.v Verilog module
# ------------------------------------------------------------------------

defs = {'i': 'input wire', 's': 'input wire', 'o': 'output wire'}

sim_file = os.path.join(outdir, "sim.v")
with open(sim_file, "w") as f:
    module_args = []
    for type, name, _, _ in port_names:
        if args.type == 'routing' and type == mux_lib.MuxPinType.SELECT:
            continue
        module_args.append(name)

    mux_prefix = {'logic': '', 'routing': 'r'}[args.type]

    f.write("/* ")
    f.write("\n * ".join(generated_with.splitlines()))
    f.write("\n */\n\n")
    f.write('`include "%s/%s/%smux%i/sim.v"\n' % (mux_dir, 'logic', '', args.width))
    f.write("\n")
    f.write("module %s(%s);\n" % (args.name_mux, ", ".join(module_args)))
    previous_type = None
    for type, name, width, index in port_names:
        if previous_type != type:
            f.write("\n")
            previous_type = type
        if args.type == 'routing' and type == mux_lib.MuxPinType.SELECT:
            if width == 1:
                f.write('\tparameter [0:0] %s = 0;\n' % (name))
            else:
                f.write('\tparameter %s %s = 0;\n' % (index, name))
            continue

        if width == 1:
            f.write('\t%s %s;\n' % (type.verilog(), name))
        else:
            f.write('\t%s %s %s;\n' % (type.verilog(), index, name))

    f.write("\n")
    f.write('\tMUX%s mux (\n' % args.width)
    for i in range(0, args.width):
        j = 0
        for type, name, width, index in port_names:
            if type != mux_lib.MuxPinType.INPUT:
                continue
            if j+width <= i:
                j += width
                continue
            break

        if width == 1:
            f.write('\t\t.I%i(%s),\n' % (i, name))
        else:
            f.write('\t\t.I%i(%s[%i]),\n' % (i, name, i-j))

    for i in range(0, args.width_bits):
        j = 0
        for type, name, width, index in port_names:
            if type != mux_lib.MuxPinType.SELECT:
                continue
            if j+width < i:
                j += width
                continue
            break

        if width == 1:
            f.write('\t\t.S%i(%s),\n' % (i, name))
        else:
            f.write('\t\t.S%i(%s[%i]),\n' % (i, name, i-j))

    for type, name, width, index in port_names:
        if type != mux_lib.MuxPinType.OUTPUT:
            continue
        break
    assert_eq(width ,  1)
    f.write('\t\t.O(%s)\n\t);\n' % name)

    f.write('endmodule\n')

output_block("sim.v", open(sim_file).read())

if args.type == 'logic':
    subckt = args.subckt or args.name_mux
    assert subckt
elif args.type == 'routing':
    assert args.subckt is None
    subckt = None

# ------------------------------------------------------------------------
# Generate the Model XML form.
# ------------------------------------------------------------------------
if args.type == 'logic':
    models_xml = ET.Element('models')
    models_xml.append(ET.Comment(xml_comment))

    model_xml = ET.SubElement(models_xml, 'model', {'name': subckt})

    input_ports = ET.SubElement(model_xml, 'input_ports')
    output_ports = ET.SubElement(model_xml, 'output_ports')
    for type, name, width, index in port_names:
        if type in (mux_lib.MuxPinType.INPUT, mux_lib.MuxPinType.SELECT):
            ET.SubElement(
                input_ports, 'port', {
                    'name': name,
                    'combinational_sink_ports': ','.join(n for t, n, w, i in port_names if t in (mux_lib.MuxPinType.OUTPUT,)),
                })
        elif type in (mux_lib.MuxPinType.OUTPUT,):
            ET.SubElement(output_ports, 'port', {'name': args.name_output})

    models_str = ET.tostring(models_xml, pretty_print=True).decode('utf-8')
    output_block("model.xml", models_str)
    with open(os.path.join(outdir, "model.xml"), "w") as f:
        f.write(models_str)
else:
    output_block("model.xml", "No model.xml for routing elements.")

# ------------------------------------------------------------------------
# Generate the pb_type XML form.
# ------------------------------------------------------------------------

pb_type_xml = mux_lib.pb_type_xml(
    mux_lib.MuxType[args.type.upper()],
    args.name_mux,
    port_names,
    subckt=subckt,
    num_pb=args.num_pb,
    comment=xml_comment)

pb_type_str = ET.tostring(pb_type_xml, pretty_print=True).decode('utf-8')
output_block("pb_type.xml", pb_type_str)
with open(os.path.join(outdir, "pb_type.xml"), "w") as f:
    f.write(pb_type_str)
