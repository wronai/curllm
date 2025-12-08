#!/usr/bin/env python3
"""
CurLLM Flow CLI - Execute YAML flow definitions

Usage:
    curllm-flow run <flow.yaml> [--var key=value]
    curllm-flow validate <flow.yaml>
    curllm-flow list [directory]
    curllm-flow info <flow.yaml>
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any

from ..streamware.yaml_runner import YAMLFlowRunner, validate_yaml_flow
from ..streamware import enable_diagnostics
from ..diagnostics import get_logger

logger = get_logger(__name__)


def _configure_diagnostics(args):
    if args.verbose:
        enable_diagnostics("DEBUG")
    elif args.quiet:
        enable_diagnostics("ERROR")
    else:
        enable_diagnostics("INFO")


def _parse_variables(args) -> Dict[str, Any]:
    variables: Dict[str, Any] = {}
    for var in args.var or []:
        if '=' in var:
            key, value = var.split('=', 1)
            variables[key] = value
        else:
            logger.warning(f"Invalid variable format: {var} (use key=value)")
    return variables


def _load_input(args):
    if args.input:
        try:
            return json.loads(args.input)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {e}") from e
    if args.input_file:
        try:
            with open(args.input_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Error reading input file: {e}") from e
    return None


def cmd_run(args):
    """Run a YAML flow"""
    _configure_diagnostics(args)
    variables = _parse_variables(args)
    try:
        input_data = _load_input(args)
    except ValueError as e:
        logger.error(e)
        return 1
    
    # Run flow
    try:
        runner = YAMLFlowRunner()
        if variables:
            runner.set_variables(variables)
        
        logger.info(f"Running flow: {args.flow}")
        result = runner.run_yaml(args.flow, input_data)
        
        # Output result
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Result written to: {args.output}")
        else:
            print(json.dumps(result, indent=2))
        
        return 0
        
    except Exception as e:
        logger.error(f"Flow execution failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_validate(args):
    """Validate a YAML flow"""
    enable_diagnostics("INFO" if args.verbose else "WARNING")
    
    try:
        is_valid = validate_yaml_flow(args.flow)
        
        if is_valid:
            print(f"✓ Flow is valid: {args.flow}")
            return 0
        else:
            print(f"✗ Flow validation failed: {args.flow}")
            return 1
            
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return 1


def cmd_list(args):
    """List available flows"""
    directory = args.directory or "flows"
    path = Path(directory)
    
    if not path.exists():
        print(f"Directory not found: {directory}")
        return 1
    
    yaml_files = list(path.glob("*.yaml")) + list(path.glob("*.yml"))
    
    if not yaml_files:
        print(f"No YAML flows found in: {directory}")
        return 0
    
    print(f"\nAvailable flows in {directory}:")
    print("=" * 60)
    
    for yaml_file in sorted(yaml_files):
        # Try to read flow name
        try:
            runner = YAMLFlowRunner()
            spec = runner.load_yaml(str(yaml_file))
            name = spec.get('name', 'Unnamed')
            description = spec.get('description', '')
            
            print(f"\n{yaml_file.name}")
            print(f"  Name: {name}")
            if description:
                print(f"  Description: {description}")
            print(f"  Steps: {len(spec.get('steps', []))}")
            
        except Exception as e:
            print(f"\n{yaml_file.name}")
            print(f"  Error: {e}")
    
    print("\n" + "=" * 60)
    print(f"Total: {len(yaml_files)} flows")
    
    return 0


FLOW_ARG_HELP = "Path to YAML flow file"


def cmd_info(args):
    """Show detailed flow information"""
    enable_diagnostics("WARNING")
    
    try:
        runner = YAMLFlowRunner()
        spec = runner.load_yaml(args.flow)
        
        print(f"\nFlow Information: {args.flow}")
        print("=" * 60)
        print(f"Name: {spec.get('name', 'Unnamed')}")
        print(f"Description: {spec.get('description', 'No description')}")
        print(f"Diagnostics: {spec.get('diagnostics', False)}")
        print(f"Trace: {spec.get('trace', False)}")
        
        if 'input' in spec:
            print("\nInput:")
            print(f"  Type: {spec['input'].get('type', 'unknown')}")
            if 'data' in spec['input']:
                print(f"  Data keys: {list(spec['input']['data'].keys())}")
        
        if 'steps' in spec:
            print(f"\nSteps ({len(spec['steps'])}):")
            for i, step in enumerate(spec['steps'], 1):
                component = step.get('component', 'unknown')
                params = step.get('params', {})
                print(f"  {i}. {component}")
                if params:
                    for key, value in params.items():
                        print(f"     - {key}: {value}")
        
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error reading flow: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="CurLLM Flow CLI - Execute YAML flow definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run a YAML flow')
    run_parser.add_argument('flow', help=FLOW_ARG_HELP)
    run_parser.add_argument('--var', '-v', action='append', help='Set variable (key=value)')
    run_parser.add_argument('--input', '-i', help='Input data as JSON string')
    run_parser.add_argument('--input-file', '-f', help='Input data from JSON file')
    run_parser.add_argument('--output', '-o', help='Output file for results')
    run_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    run_parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')
    run_parser.set_defaults(func=cmd_run)
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a YAML flow')
    validate_parser.add_argument('flow', help=FLOW_ARG_HELP)
    validate_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    validate_parser.set_defaults(func=cmd_validate)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available flows')
    list_parser.add_argument('directory', nargs='?', default='flows', help='Directory to search')
    list_parser.set_defaults(func=cmd_list)
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show flow information')
    info_parser.add_argument('flow', help=FLOW_ARG_HELP)
    info_parser.set_defaults(func=cmd_info)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
