import React, { Component, MouseEvent } from "react";
import { ReactComponent as Lemon } from "./image/lemon.svg";
import { ReactComponent as RightArrows } from "./image/right_arrows.svg";
import { ReactComponent as LeftArrows } from "./image/left_arrows.svg";

type EntryProps = {
  year: bigint;
  title: string;
  assets: Array<string>;
  description: string;
};

type EntryState = {
  selected: bigint;
};

type GalleryProps = {
  count: bigint;
  metadata: Map<string, EntryProps>;
};

type GalleryState = {
  entries: Array<EntryProps>;
  showing: bigint;
};

export class Gallery extends Component<GalleryProps, GalleryState> {
  constructor(props: GalleryProps) {
    super(props);
    this.state = { showing: 2n, entries: [] };
  }

  componentDidMount = () => {
    this.generateEntries();
  };

  render = (): JSX.Element => {
    if (this.state.entries.length === 0) {
      return <div>Loading galleries...</div>;
    }

    return (
      <div className="gallery">
        {this.state.entries.map((metadata, index) => (
          <GalleryEntry key={index} {...metadata} />
        ))}
      </div>
    );
  };

  onMoreClick = (_evt: MouseEvent<HTMLButtonElement>) => {
    if (this.state.showing < this.props.count) {
      var showing = this.state.showing + 2n;
      if (showing > this.props.count) {
        this.setState({ showing: this.props.count });
      } else {
        this.setState({ showing: showing });
      }
    }
  };

  generateEntries = (): void => {
    const entries: Array<EntryProps> = [];
    var i = 0n;
    while (i < this.props.count) {
      const metadata: EntryProps | undefined = this.props.metadata.get(
        String(i)
      );
      if (metadata === undefined) {
        throw Error("gallery length was wrong, shouldn't happen");
      }
      entries.push(metadata);
      i += 1n;
    }

    this.setState({ entries: entries });
  };
}

class GalleryEntry extends Component<EntryProps, EntryState> {
  constructor(props: EntryProps) {
    super(props);
    this.state = { selected: 0n };
  }

  render = () => {
    const dots: Array<JSX.Element> = [];
    for (let i = 0n; i < this.props.assets.length; i += 1n) {
      let type = "non-selected";
      let color =  "#C39CF5";
      if (i === this.state.selected) {
        type = "selected";
        color = "#3D3D3D";
      } 
      dots.push(<circle className={"gallery-dot " + type} onClick={this.onSetSelected(i)} cx={String(2n + i * 5n)} cy="2" r="2" fill={color} />);
    }

    /* <!-- not the biggest fan of whatever the title is trying to be --> */
    return (
      <div className="gallery-entry">
        <div className="info-title">
          <Lemon className="lemon" />
          <span className="heading">{this.props.title}</span>
          <div className="years year-pill center">{String(this.props.year)}</div>
        </div>

        <div className="gallery-main-group">
          <span className="gallery-b-container">
            <button className="gallery-button" onClick={this.onMoveLeft}>
              <LeftArrows width="100%" />
            </button>
          </span>
          <img
            className="gallery-image"
            src={
              "levboard/gallery/" +
              this.props.assets[Number(this.state.selected)]
            }
          />
          <span className="gallery-b-container">
            <button className="gallery-button" onClick={this.onMoveRight}>
              <RightArrows width="100%" />
            </button>
          </span>
        </div>
        <div className="entry-dots center">
          <svg
            width={this.props.assets.length * 15 - 3}
            height={"12"}
            viewBox={"0 0 " + (this.props.assets.length * 5 - 1) + " 4"}
          >
            {dots}
          </svg>
        </div>
      </div>
    );
  };

  onSetSelected: (index: bigint) => (_evt: MouseEvent) => void = (index) => {
    return (_evt: MouseEvent) => {
      if (index < 0n || index >= BigInt(this.props.assets.length)) {
        throw Error("index out of bounds for assets");
      }
      this.setState({ selected: index });
    };
  };

  // bumps the image to the right
  onMoveRight = (_evt: MouseEvent<HTMLButtonElement>) => {
    const newSelected =
      (this.state.selected + 1n) % BigInt(this.props.assets.length);
    this.setState({ selected: newSelected });
  };

  // bumps the image to the left
  onMoveLeft = (_evt: MouseEvent<HTMLButtonElement>) => {
    const newSelected =
      // this is kinda dumb, but if we don't add the length of assets, it will be
      // totally happy sending in a negative number, like -1 and -2 if we have
      // three total items.
      (this.state.selected - 1n + BigInt(this.props.assets.length)) %
      BigInt(this.props.assets.length);
    this.setState({ selected: newSelected });
  };
}
