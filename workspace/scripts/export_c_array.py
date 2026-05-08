import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output-c', type=str, required=True)
    parser.add_argument('--output-h', type=str, required=True)
    parser.add_argument('--symbol', type=str, default='g_llie_model_data')
    args = parser.parse_args()

    data = Path(args.input).read_bytes()
    arr = ','.join(str(b) for b in data)
    Path(args.output_h).write_text(
        f'extern const unsigned char {args.symbol}[];\nextern const unsigned int {args.symbol}_len;\n',
        encoding='utf-8'
    )
    Path(args.output_c).write_text(
        f'#include "{Path(args.output_h).name}"\nconst unsigned char {args.symbol}[] = {{{arr}}};\nconst unsigned int {args.symbol}_len = {len(data)};\n',
        encoding='utf-8'
    )
    print('wrote', args.output_c, args.output_h)


if __name__ == '__main__':
    main()
