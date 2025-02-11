import React, { Component } from "react";
import flourish from "./data/flourish.json";
import metadata from "./data/metadata.json";
import { ReactComponent as Lemon } from "./image/lemon.svg";

const HEIGHT = 214;

type AlbumMetadata = {
  album: string;
  color: string;
  image: string;
};

type FlourishEntry = {
  start: string;
  end: string;
  albums: Array<string>;
  weeks: bigint;
};

type AppProps = {}; // no props

type AppState = {
  metadata: Map<string, AlbumMetadata>;
  flourish: Map<string, FlourishEntry>;
  dates: Array<string>;
  width?: bigint;
  elements?: Array<JSX.Element>;
};

/** THINSPO:
 * https://jsfiddle.net/8xdozwy4/
 */

/** Top-level component that displays the entire UI. */
export class App extends Component<AppProps, AppState> {
  constructor(props: AppProps) {
    super(props);

    this.state = {
      metadata: new Map(Object.entries(metadata)),
      flourish: new Map(Object.entries(flourish)),
      dates: Object.keys(flourish),
    };
  }

  componentDidMount = () => {
    this.setState({ elements: this.generateElements() });
  };

  render = (): JSX.Element => {
    if (this.state.width === undefined) {
      return <div>Loading information...</div>;
    }
    return (
      <div className="center-column">
        <div className="title">
          <Lemon />
          <text className="heading">ALL-TIME ALBUMS</text>
        </div>
        <div className="scroller">
          <svg
            id="svg"
            width={String(this.state.width * 3n)}
            height={String(HEIGHT * 3)}
            viewBox={"0 0 " + this.state.width + " " + HEIGHT}
          >
            {this.state.elements}
          </svg>
        </div>
      </div>
    );
  };

  generateElements = (): Array<JSX.Element> => {
    const items: Array<JSX.Element> = [];

    let xOffset: bigint = 0n;
    let column: bigint = 0n;
    let album: string;
    let albuminfo: AlbumMetadata;
    let information: FlourishEntry;

    while (Number(column) < this.state.dates.length) {
      const hold: FlourishEntry | undefined = this.state.flourish.get(
        this.state.dates[Number(column)]
      );
      if (hold === undefined) {
        throw new Error("shoudldn't happen.");
      } else {
        information = hold;
      }
      for (let i = 0; i < 10; i++) {
        album = information.albums[i];
        const albuminformation: AlbumMetadata | undefined =
          this.state.metadata.get(album);
        if (albuminformation === undefined) {
          throw new Error("shouldn't happen");
        }
        albuminfo = albuminformation;

        items.push(
          <image
            href={String(albuminfo.image)}
            width="16"
            height="16"
            x={String(xOffset)}
            y={String(i * 20 + 8)}
            key={album + "-" + column}
          />
        );
        let barOffset: bigint = 1n;
        while (barOffset < information.weeks) {
          items.push(
            <rect
              width="1"
              height="16"
              x={String(xOffset + 15n + barOffset * 2n)}
              y={String(i * 20 + 8)}
              fill={"#" + albuminfo.color}
              key={album + "-" + column + "-" + barOffset}
            />
          );
          barOffset += 1n;
        }
      }

      let header: string;

      // we gotta do this becasue ISO format does "02-08", which we would much
      // rather have as "2.8"
      console.log(information.start, information.end);
      const start_month = Number(information.start.split("-")[1]).toString();
      const start_day = Number(information.start.split("-")[2]).toString();
      const end_month = Number(information.end.split("-")[1]).toString();
      const end_day = Number(information.end.split("-")[2]).toString();

      const start = start_month + "." + start_day;
      const end = end_month + "." + end_day;

      console.log(start, end);

      if (information.weeks == 1n) {
        header = start;
      } else {
        // i have no clue why it has to be in this order for it to be in the correct
        // order when it gets sent out...
        header = end + " - " + start;
      }

      // add header text
      items.push(
        <text
          x={String(xOffset + 7n + BigInt(information.weeks))}
          y="4"
          className="label"
          key={"top-label-" + column}
        >
          {header}
        </text>,
        <text
          x={String(xOffset + 7n + BigInt(information.weeks))}
          y="210"
          className="label"
          key={"bottom-label-" + column}
        >
          {header}
        </text>
      );

      console.log("column " + column + " finished.");
      xOffset += 18n + 2n * BigInt(information.weeks);
      column += 1n;
    }
    this.setState({ width: xOffset });
    return items;
  };
}
